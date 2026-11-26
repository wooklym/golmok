// golmok-objcap — Apple Object Capture (RealityKit PhotogrammetrySession) command-line wrapper.
//
// WP-21 (D-022): candidate Mac replacement for the RealityScan mesh step of D-005. It only calls the public
// RealityKit API and writes what the API returns; `run` does not convert coordinates (only the experimental
// `colmap` subcommand in Colmap.swift does, with a measured convention). See README.md.
//
//   golmok-objcap limits
//   golmok-objcap run <imageFolder> <outDir> [--detail preview|reduced|medium|full|raw] [--format obj|usdz|both]
//                     [--ordering sequential|unordered] [--sensitivity normal|high] [--poses] [--point-cloud]
//                     [--no-object-masking] [--ignore-bounding-box] [--checkpoint <dir>]
//   golmok-objcap colmap <poses.json> <outDir> [<pointcloud.ply>]   (EXPERIMENTAL, Colmap.swift)
//
// Exit codes: 0 success, 1 processing failed or a requested output is missing, 2 usage error,
// 3 PhotogrammetrySession not supported on this machine.

import CoreGraphics
import Foundation
import ImageIO
import RealityKit
import simd

let toolVersion = "0.1.0"

// MARK: - small helpers

func eprint(_ s: String) {
    FileHandle.standardError.write((s + "\n").data(using: .utf8)!)
}

func sysctlString(_ name: String) -> String? {
    var size = 0
    guard sysctlbyname(name, nil, &size, nil, 0) == 0, size > 0 else { return nil }
    var buf = [CChar](repeating: 0, count: size)
    guard sysctlbyname(name, &buf, &size, nil, 0) == 0 else { return nil }
    return String(cString: buf)
}

func sysctlUInt64(_ name: String) -> UInt64? {
    var v: UInt64 = 0
    var size = MemoryLayout<UInt64>.size
    guard sysctlbyname(name, &v, &size, nil, 0) == 0 else { return nil }
    return v
}

func machineInfo() -> [String: Any] {
    let os = ProcessInfo.processInfo.operatingSystemVersion
    var info: [String: Any] = [
        "os_version": "\(os.majorVersion).\(os.minorVersion).\(os.patchVersion)",
        "os_version_string": ProcessInfo.processInfo.operatingSystemVersionString,
        "active_processor_count": ProcessInfo.processInfo.activeProcessorCount,
        "physical_memory_bytes": ProcessInfo.processInfo.physicalMemory,
    ]
    if let m = sysctlString("hw.model") { info["hw_model"] = m }
    if let c = sysctlString("machdep.cpu.brand_string") { info["cpu"] = c }
    if let b = sysctlString("kern.osversion") { info["os_build"] = b }
    if let p = sysctlUInt64("hw.perflevel0.physicalcpu") { info["performance_cores"] = p }
    if let e = sysctlUInt64("hw.perflevel1.physicalcpu") { info["efficiency_cores"] = e }
    return info
}

func d(_ f: Float) -> Double { Double(f) }

/// simd matrices are column-major; JSON gets them as rows (mathematical layout: rows[i][j] = M[i, j]).
func rows(_ m: simd_float4x4) -> [[Double]] {
    (0..<4).map { r in (0..<4).map { c in d(m[c][r]) } }
}

func rows(_ m: simd_float3x3) -> [[Double]] {
    (0..<3).map { r in (0..<3).map { c in d(m[c][r]) } }
}

func writeJSON(_ obj: Any, to url: URL) throws {
    let data = try JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: url)
}

func printJSON(_ obj: Any) {
    if let data = try? JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys]),
       let s = String(data: data, encoding: .utf8) {
        print(s)
    }
}

func isoNow() -> String { ISO8601DateFormatter().string(from: Date()) }

/// Pixel size and EXIF orientation of an image file, read with ImageIO (not part of the PhotogrammetrySession output).
func imageInfo(_ url: URL) -> [String: Any]? {
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let props = CGImageSourceCopyPropertiesAtIndex(src, 0, nil) as? [CFString: Any] else { return nil }
    var out: [String: Any] = [:]
    if let w = props[kCGImagePropertyPixelWidth] as? Int { out["pixel_width"] = w }
    if let h = props[kCGImagePropertyPixelHeight] as? Int { out["pixel_height"] = h }
    if let o = props[kCGImagePropertyOrientation] as? Int { out["exif_orientation"] = o }
    if let exif = props[kCGImagePropertyExifDictionary] as? [CFString: Any] {
        if let fl = exif[kCGImagePropertyExifFocalLength] as? Double { out["exif_focal_length_mm"] = fl }
        if let fl35 = exif[kCGImagePropertyExifFocalLenIn35mmFilm] as? Int { out["exif_focal_length_35mm"] = fl35 }
    }
    return out
}

func directorySize(_ url: URL) -> Int64 {
    var isDir: ObjCBool = false
    guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir) else { return 0 }
    if !isDir.boolValue {
        return (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? Int64) ?? 0
    }
    var total: Int64 = 0
    if let e = FileManager.default.enumerator(at: url, includingPropertiesForKeys: [.fileSizeKey]) {
        for case let f as URL in e {
            total += Int64((try? f.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0)
        }
    }
    return total
}

func listFiles(_ url: URL) -> [[String: Any]] {
    var isDir: ObjCBool = false
    guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir) else { return [] }
    if !isDir.boolValue { return [["path": url.lastPathComponent, "bytes": directorySize(url)]] }
    var out: [[String: Any]] = []
    if let e = FileManager.default.enumerator(at: url, includingPropertiesForKeys: [.fileSizeKey, .isRegularFileKey]) {
        for case let f as URL in e {
            guard (try? f.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true else { continue }
            let rel = f.path.replacingOccurrences(of: url.deletingLastPathComponent().path + "/", with: "")
            out.append(["path": rel, "bytes": Int64((try? f.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0)])
        }
    }
    return out.sorted { ($0["path"] as! String) < ($1["path"] as! String) }
}

// MARK: - usage

let usage = """
usage:
  golmok-objcap limits
  golmok-objcap run <imageFolder> <outDir> [options]
  golmok-objcap colmap <poses.json> <outDir> [<pointcloud.ply>]   EXPERIMENTAL COLMAP text export (README)

run options:
  --detail preview|reduced|medium|full|raw   model detail level (default: medium)
  --format obj|usdz|both                     model file kind (default: obj; OBJ goes to <outDir>/obj/)
  --ordering sequential|unordered            Configuration.sampleOrdering (default: unordered)
  --sensitivity normal|high                  Configuration.featureSensitivity (default: normal)
  --poses                                    also request .poses, written to <outDir>/poses.json
  --point-cloud                              also request .pointCloud, written to <outDir>/pointcloud.ply
  --no-object-masking                        Configuration.isObjectMaskingEnabled = false
  --ignore-bounding-box                      Configuration.ignoreBoundingBox = true (macOS 15+)
  --checkpoint <dir>                         Configuration.checkpointDirectory
Writes <outDir>/summary.json (settings, timing, warnings, output files). Exit 0 ok, 1 failed, 2 usage, 3 unsupported.
"""

func usageError(_ msg: String) -> Never {
    eprint("golmok-objcap: \(msg)\n\n\(usage)")
    exit(2)
}

// MARK: - limits

func limitsReport() -> [String: Any] {
    var out: [String: Any] = ["tool": "golmok-objcap", "tool_version": toolVersion, "machine": machineInfo()]
    if #available(macOS 13.0, *) {
        out["isSupported"] = PhotogrammetrySession.isSupported
    }
    if #available(macOS 14.0, *) {
        let l = PhotogrammetrySession.limits
        out["limits"] = [
            "maximumNumberOfInputImages": l.maximumNumberOfInputImages,
            "maximumInputImageDimension": l.maximumInputImageDimension,
        ]
    } else {
        out["limits"] = "PhotogrammetrySession.Limits needs macOS 14"
    }
    var api: [String: Bool] = [:]
    if #available(macOS 15.0, *) { api["macOS15_ignoreBoundingBox_meshPrimitive_sixteenK"] = true }
    if #available(macOS 26.0, *) { api["macOS26_pose_intrinsics_lensDistortionData"] = true }
    out["api_availability"] = api
    return out
}

// MARK: - run

struct RunOptions {
    var input: URL
    var outDir: URL
    var detail: PhotogrammetrySession.Request.Detail = .medium
    var detailName = "medium"
    var format = "obj"
    var ordering: PhotogrammetrySession.Configuration.SampleOrdering = .unordered
    var orderingName = "unordered"
    var sensitivity: PhotogrammetrySession.Configuration.FeatureSensitivity = .normal
    var sensitivityName = "normal"
    var poses = false
    var pointCloud = false
    var objectMasking = true
    var ignoreBoundingBox = false
    var checkpoint: URL?
}

func parseRun(_ args: [String]) -> RunOptions {
    var positional: [String] = []
    var o = RunOptions(input: URL(fileURLWithPath: "/"), outDir: URL(fileURLWithPath: "/"))
    var i = 0
    func value(_ flag: String) -> String {
        i += 1
        guard i < args.count else { usageError("\(flag) needs a value") }
        return args[i]
    }
    while i < args.count {
        let a = args[i]
        switch a {
        case "--detail":
            let v = value(a)
            switch v {
            case "preview": o.detail = .preview
            case "reduced": o.detail = .reduced
            case "medium": o.detail = .medium
            case "full": o.detail = .full
            case "raw": o.detail = .raw
            default: usageError("unknown --detail \(v)")
            }
            o.detailName = v
        case "--format":
            let v = value(a)
            guard ["obj", "usdz", "both"].contains(v) else { usageError("unknown --format \(v)") }
            o.format = v
        case "--ordering":
            let v = value(a)
            switch v {
            case "sequential": o.ordering = .sequential
            case "unordered": o.ordering = .unordered
            default: usageError("unknown --ordering \(v)")
            }
            o.orderingName = v
        case "--sensitivity":
            let v = value(a)
            switch v {
            case "normal": o.sensitivity = .normal
            case "high": o.sensitivity = .high
            default: usageError("unknown --sensitivity \(v)")
            }
            o.sensitivityName = v
        case "--poses": o.poses = true
        case "--point-cloud": o.pointCloud = true
        case "--no-object-masking": o.objectMasking = false
        case "--ignore-bounding-box": o.ignoreBoundingBox = true
        case "--checkpoint": o.checkpoint = URL(fileURLWithPath: value(a), isDirectory: true)
        default:
            if a.hasPrefix("--") { usageError("unknown option \(a)") }
            positional.append(a)
        }
        i += 1
    }
    guard positional.count == 2 else { usageError("run needs <imageFolder> <outDir>") }
    o.input = URL(fileURLWithPath: positional[0], isDirectory: true).standardizedFileURL
    o.outDir = URL(fileURLWithPath: positional[1], isDirectory: true).standardizedFileURL
    return o
}

func requestKey(_ r: PhotogrammetrySession.Request) -> String {
    switch r {
    case .modelFile(let url, _, _): return url.pathExtension.lowercased() == "usdz" ? "model_usdz" : "model_obj"
    case .modelEntity: return "model_entity"
    case .bounds: return "bounds"
    case .pointCloud: return "point_cloud"
    case .poses: return "poses"
    @unknown default: return "unknown"
    }
}

func stageName(_ s: PhotogrammetrySession.Output.ProcessingStage?) -> String {
    guard let s else { return "unknown" }
    switch s {
    case .preProcessing: return "preProcessing"
    case .imageAlignment: return "imageAlignment"
    case .pointCloudGeneration: return "pointCloudGeneration"
    case .meshGeneration: return "meshGeneration"
    case .textureMapping: return "textureMapping"
    case .optimization: return "optimization"
    @unknown default: return "unknown(\(s))"
    }
}

func posesJSON(_ poses: PhotogrammetrySession.Poses) -> [String: Any] {
    let urls = poses.urlsBySample
    var samples: [[String: Any]] = []
    for id in poses.posesBySample.keys.sorted() {
        let p = poses.posesBySample[id]!
        let t = p.translation
        let q = p.rotation
        var s: [String: Any] = [
            "sample_id": id,
            "translation": [d(t.x), d(t.y), d(t.z)],
            "rotation_quaternion_xyzw": [d(q.imag.x), d(q.imag.y), d(q.imag.z), d(q.real)],
            "transform_matrix_rows": rows(p.transform.matrix),
        ]
        if let u = urls[id] {
            s["image"] = u.lastPathComponent
            if let info = imageInfo(u) { s["image_file_info"] = info }
        }
        if #available(macOS 26.0, *) {
            if let k = p.intrinsics {
                s["intrinsics_rows"] = rows(k)
            } else {
                s["intrinsics_rows"] = NSNull()
            }
            if let ld = p.lensDistortionData {
                s["lens_distortion"] = [
                    "center": [d(ld.center.x), d(ld.center.y)],
                    "radial_lookup_table": ld.radialLookupTable.map { d($0) },
                ]
            } else {
                s["lens_distortion"] = NSNull()
            }
        }
        samples.append(s)
    }
    return [
        "format": "golmok-objcap poses v1",
        "notes": [
            "Values are PhotogrammetrySession.Poses as returned (float32 widened to double). No conversion applied.",
            "translation / rotation_quaternion_xyzw / transform_matrix_rows: Pose.translation, Pose.rotation (simd_quatf imag xyz + real w), Pose.transform.matrix written as rows.",
            "Apple documents the pose as 'a 6DOF pose relative to the estimated coordinate system'; it does not document camera axis directions or units. See README.md.",
            "intrinsics_rows / lens_distortion: Pose.intrinsics and Pose.lensDistortionData (macOS 26+), null when the API returned nil.",
            "image_file_info is read by golmok-objcap from the image file with ImageIO; it is not part of the API output.",
        ],
        "sample_count": samples.count,
        "samples": samples,
    ]
}

func writePLY(_ cloud: PhotogrammetrySession.PointCloud, to url: URL) throws {
    var data = Data()
    let header = """
    ply
    format binary_little_endian 1.0
    comment golmok-objcap PhotogrammetrySession.PointCloud (sparse), positions as returned
    element vertex \(cloud.points.count)
    property float x
    property float y
    property float z
    property uchar red
    property uchar green
    property uchar blue
    property uchar alpha
    end_header\n
    """
    data.append(header.data(using: .ascii)!)
    data.reserveCapacity(header.count + cloud.points.count * 16)
    for p in cloud.points {
        let xyz = [p.position.x, p.position.y, p.position.z].map { $0.bitPattern.littleEndian }
        xyz.withUnsafeBytes { data.append(contentsOf: $0) }
        data.append(contentsOf: [p.color.x, p.color.y, p.color.z, p.color.w])
    }
    try data.write(to: url)
}

final class RunState {
    var started = Date()
    var stageFirstSeen: [String: Double] = [:]
    var lastStage: [String: String] = [:]
    var lastPrint = Date.distantPast
    var invalidSamples: [[String: Any]] = []
    var skippedSamples: [Int] = []
    var automaticDownsampling = false
    var stitchingIncomplete = false
    var inputCompleteAt: Double?
    var results: [String: Any] = [:]
    var errors: [String: String] = [:]
    var completed = Set<String>()
    var cancelled = false

    func elapsed() -> Double { Date().timeIntervalSince(started) }
}

@available(macOS 14.0, *)
func runCommand(_ o: RunOptions) async -> Int32 {
    guard PhotogrammetrySession.isSupported else {
        eprint("golmok-objcap: PhotogrammetrySession.isSupported == false on this machine")
        return 3
    }
    let fm = FileManager.default
    var isDir: ObjCBool = false
    guard fm.fileExists(atPath: o.input.path, isDirectory: &isDir), isDir.boolValue else {
        eprint("golmok-objcap: image folder not found: \(o.input.path)")
        return 2
    }
    do { try fm.createDirectory(at: o.outDir, withIntermediateDirectories: true) } catch {
        eprint("golmok-objcap: cannot create \(o.outDir.path): \(error)")
        return 2
    }

    var config = PhotogrammetrySession.Configuration()
    config.sampleOrdering = o.ordering
    config.featureSensitivity = o.sensitivity
    config.isObjectMaskingEnabled = o.objectMasking
    if o.ignoreBoundingBox {
        if #available(macOS 15.0, *) { config.ignoreBoundingBox = true } else {
            eprint("golmok-objcap: --ignore-bounding-box needs macOS 15; ignored")
        }
    }
    if let c = o.checkpoint {
        try? fm.createDirectory(at: c, withIntermediateDirectories: true)
        config.checkpointDirectory = c
    }

    var requests: [PhotogrammetrySession.Request] = []
    let objDir = o.outDir.appendingPathComponent("obj", isDirectory: true)
    let usdzURL = o.outDir.appendingPathComponent("model-\(o.detailName).usdz")
    if o.format == "obj" || o.format == "both" {
        try? fm.createDirectory(at: objDir, withIntermediateDirectories: true)
        requests.append(.modelFile(url: objDir, detail: o.detail))
    }
    if o.format == "usdz" || o.format == "both" {
        requests.append(.modelFile(url: usdzURL, detail: o.detail))
    }
    if o.poses { requests.append(.poses) }
    if o.pointCloud { requests.append(.pointCloud) }
    let wanted = Set(requests.map(requestKey))

    let st = RunState()
    let session: PhotogrammetrySession
    do {
        session = try PhotogrammetrySession(input: o.input, configuration: config)
    } catch {
        eprint("golmok-objcap: PhotogrammetrySession init failed: \(error)")
        return 1
    }
    eprint("golmok-objcap: session \(session.id) input=\(o.input.path) requests=\(wanted.sorted())")

    let outDir = o.outDir
    let consumer = Task { () -> Void in
        do {
            for try await output in session.outputs {
                switch output {
                case .inputComplete:
                    st.inputCompleteAt = st.elapsed()
                    eprint(String(format: "[%7.1fs] input complete", st.elapsed()))
                case .requestProgress(let r, let fraction):
                    if Date().timeIntervalSince(st.lastPrint) > 5 {
                        st.lastPrint = Date()
                        let key = requestKey(r)
                        eprint(String(format: "[%7.1fs] %@ %5.1f%% (stage %@)", st.elapsed(), key,
                                      fraction * 100, st.lastStage[key] ?? "-"))
                    }
                case .requestProgressInfo(let r, let info):
                    let s = stageName(info.processingStage)
                    let key = requestKey(r)
                    if s != st.lastStage[key] {
                        st.lastStage[key] = s
                        if st.stageFirstSeen[s] == nil { st.stageFirstSeen[s] = st.elapsed() }
                        let eta = info.estimatedRemainingTime.map { String(format: "%.0fs", $0) } ?? "?"
                        eprint(String(format: "[%7.1fs] %@ stage %@ (eta %@)", st.elapsed(), key, s, eta))
                    }
                case .requestComplete(let r, let result):
                    let key = requestKey(r)
                    st.completed.insert(key)
                    eprint(String(format: "[%7.1fs] %@ complete", st.elapsed(), key))
                    switch result {
                    case .modelFile(let url):
                        st.results[key] = ["url": url.path, "bytes": directorySize(url), "files": listFiles(url),
                                           "completed_at_s": st.elapsed()]
                    case .poses(let poses):
                        let url = outDir.appendingPathComponent("poses.json")
                        do {
                            try writeJSON(posesJSON(poses), to: url)
                            st.results[key] = ["url": url.path, "sample_count": poses.posesBySample.count,
                                               "completed_at_s": st.elapsed()]
                        } catch { st.errors[key] = "write poses.json: \(error)" }
                    case .pointCloud(let cloud):
                        let url = outDir.appendingPathComponent("pointcloud.ply")
                        do {
                            try writePLY(cloud, to: url)
                            st.results[key] = ["url": url.path, "point_count": cloud.points.count,
                                               "completed_at_s": st.elapsed()]
                        } catch { st.errors[key] = "write pointcloud.ply: \(error)" }
                    case .bounds(let b):
                        st.results[key] = ["min": [d(b.min.x), d(b.min.y), d(b.min.z)],
                                           "max": [d(b.max.x), d(b.max.y), d(b.max.z)]]
                    default:
                        st.results[key] = "unhandled result"
                    }
                case .requestError(let r, let error):
                    let key = requestKey(r)
                    st.errors[key] = "\(error)"
                    eprint(String(format: "[%7.1fs] %@ ERROR: %@", st.elapsed(), key, "\(error)"))
                case .processingComplete:
                    eprint(String(format: "[%7.1fs] processing complete", st.elapsed()))
                    return
                case .processingCancelled:
                    st.cancelled = true
                    eprint("golmok-objcap: processing cancelled")
                    return
                case .invalidSample(let id, let reason):
                    st.invalidSamples.append(["id": id, "reason": reason])
                    eprint("invalid sample \(id): \(reason)")
                case .skippedSample(let id):
                    st.skippedSamples.append(id)
                    eprint("skipped sample \(id)")
                case .automaticDownsampling:
                    st.automaticDownsampling = true
                    eprint("automatic downsampling enabled by the session")
                case .stitchingIncomplete:
                    st.stitchingIncomplete = true
                    eprint("WARNING: stitching incomplete (not all images could be connected)")
                @unknown default:
                    eprint("output: \(output)")
                }
            }
        } catch {
            st.errors["outputs"] = "\(error)"
            eprint("golmok-objcap: output stream error: \(error)")
        }
    }

    do {
        try session.process(requests: requests)
    } catch {
        eprint("golmok-objcap: process(requests:) failed: \(error)")
        session.cancel()
        _ = await consumer.result
        return 1
    }
    _ = await consumer.result

    let missing = wanted.subtracting(st.completed).subtracting(st.errors.keys)
    for m in missing { st.errors[m] = "no requestComplete received" }
    let ok = st.errors.isEmpty && !st.cancelled

    let inputImages = (try? fm.contentsOfDirectory(atPath: o.input.path))?.filter { !$0.hasPrefix(".") }.count ?? 0
    let summary: [String: Any] = [
        "tool": "golmok-objcap",
        "tool_version": toolVersion,
        "started": ISO8601DateFormatter().string(from: st.started),
        "finished": isoNow(),
        "wall_time_s": st.elapsed(),
        "ok": ok,
        "machine": machineInfo(),
        "limits": [
            "maximumNumberOfInputImages": PhotogrammetrySession.limits.maximumNumberOfInputImages,
            "maximumInputImageDimension": PhotogrammetrySession.limits.maximumInputImageDimension,
        ],
        "input": ["folder": o.input.path, "entries": inputImages],
        "settings": [
            "detail": o.detailName, "format": o.format, "sampleOrdering": o.orderingName,
            "featureSensitivity": o.sensitivityName, "isObjectMaskingEnabled": o.objectMasking,
            "ignoreBoundingBox": o.ignoreBoundingBox, "poses": o.poses, "pointCloud": o.pointCloud,
            "checkpointDirectory": o.checkpoint?.path ?? NSNull(),
        ],
        "input_complete_at_s": st.inputCompleteAt ?? NSNull(),
        "stage_first_seen_s": st.stageFirstSeen,
        "invalid_samples": st.invalidSamples,
        "skipped_samples": st.skippedSamples,
        "automatic_downsampling": st.automaticDownsampling,
        "stitching_incomplete": st.stitchingIncomplete,
        "results": st.results,
        "errors": st.errors,
        "cancelled": st.cancelled,
    ]
    do { try writeJSON(summary, to: o.outDir.appendingPathComponent("summary.json")) } catch {
        eprint("golmok-objcap: cannot write summary.json: \(error)")
    }
    eprint(String(format: "golmok-objcap: %@ in %.1fs -> %@", ok ? "OK" : "FAILED", st.elapsed(),
                  o.outDir.appendingPathComponent("summary.json").path))
    return ok ? 0 : 1
}

// MARK: - entry point

var argv = Array(CommandLine.arguments.dropFirst())
guard let command = argv.first else { usageError("missing command") }
argv.removeFirst()

switch command {
case "limits":
    let report = limitsReport()
    printJSON(report)
    exit((report["isSupported"] as? Bool) == true ? 0 : 3)
case "run":
    let opts = parseRun(argv)
    if #available(macOS 14.0, *) {
        exit(await runCommand(opts))
    } else {
        eprint("golmok-objcap: run needs macOS 14 (PhotogrammetrySession.Limits / poses)")
        exit(3)
    }
case "colmap":
    exit(colmapCommand(argv))
case "--version", "version":
    print("golmok-objcap \(toolVersion)")
case "-h", "--help", "help":
    print(usage)
default:
    usageError("unknown command \(command)")
}
