// golmok-objcap colmap — EXPERIMENTAL: poses.json (+ pointcloud.ply) -> COLMAP text model (cameras/images/points3D.txt).
//
// The axis convention used here is NOT documented by Apple. It was measured on one public data set
// (AliceVision Buddha, CC BY 4.0) against the data set's own projection matrices, see README.md
// "좌표계와 COLMAP 변환":
//   Pose.transform = camera-to-world, camera axes x right, y up, z backward (camera looks along -Z).
// COLMAP wants world-to-camera with x right, y down, z forward, so
//   R_c2w_cv = R_pose * diag(1, -1, -1);  R_w2c = R_c2w_cv^T;  t_w2c = -R_w2c * C  (C = Pose.translation)
// Cameras are written as PINHOLE from Pose.intrinsics. Pose.lensDistortionData (a radial look-up table, not a
// COLMAP camera model) is NOT applied: either rectify the images first or accept the residual; the largest
// relative magnification in the table is printed so the error can be judged.
// points3D.txt gets the sparse point cloud with empty tracks (ERROR = 0). Whether a given splat trainer accepts
// empty tracks is unverified.

import Foundation
import simd

func colmapCommand(_ args: [String]) -> Int32 {
    guard args.count == 2 || args.count == 3 else {
        eprint("usage: golmok-objcap colmap <poses.json> <outDir> [<pointcloud.ply>]")
        return 2
    }
    let posesURL = URL(fileURLWithPath: args[0])
    let outDir = URL(fileURLWithPath: args[1], isDirectory: true)
    guard let data = try? Data(contentsOf: posesURL),
          let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let samples = root["samples"] as? [[String: Any]] else {
        eprint("golmok-objcap colmap: cannot read \(posesURL.path)")
        return 2
    }
    var cameras = "# Camera list with one line of data per camera:\n#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n"
    var images = "# Image list with two lines of data per image:\n#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n#   POINTS2D[] as (X, Y, POINT3D_ID)\n"
    var maxMag = 0.0
    var written = 0
    let flip = simd_double3x3(diagonal: SIMD3<Double>(1, -1, -1))
    for s in samples {
        guard let name = s["image"] as? String,
              let t = s["translation"] as? [Double], t.count == 3,
              let m = s["transform_matrix_rows"] as? [[Double]], m.count == 4,
              let k = s["intrinsics_rows"] as? [[Double]], k.count == 3,
              let info = s["image_file_info"] as? [String: Any],
              let w = info["pixel_width"] as? Int, let h = info["pixel_height"] as? Int else {
            eprint("golmok-objcap colmap: sample \(s["sample_id"] ?? "?") lacks image/pose/intrinsics; skipped")
            continue
        }
        if let ld = s["lens_distortion"] as? [String: Any], let lut = ld["radial_lookup_table"] as? [Double] {
            maxMag = max(maxMag, lut.map { abs($0) }.max() ?? 0)
        }
        // rows -> simd (column-major): column c = (m[0][c], m[1][c], m[2][c])
        let rPose = simd_double3x3(columns: (
            SIMD3(m[0][0], m[1][0], m[2][0]), SIMD3(m[0][1], m[1][1], m[2][1]), SIMD3(m[0][2], m[1][2], m[2][2])))
        let rW2C = (rPose * flip).transpose
        let c = SIMD3<Double>(t[0], t[1], t[2])
        let tW2C = -(rW2C * c)
        let q = simd_quatd(rW2C)
        let id = written + 1
        cameras += "\(id) PINHOLE \(w) \(h) \(k[0][0]) \(k[1][1]) \(k[0][2]) \(k[1][2])\n"
        images += "\(id) \(q.real) \(q.imag.x) \(q.imag.y) \(q.imag.z) \(tW2C.x) \(tW2C.y) \(tW2C.z) \(id) \(name)\n\n"
        written += 1
    }
    var points = "# 3D point list with one line of data per point:\n#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n"
    var pointCount = 0
    if args.count == 3 {
        guard let ply = try? Data(contentsOf: URL(fileURLWithPath: args[2])),
              let range = ply.range(of: "end_header\n".data(using: .ascii)!),
              let header = String(data: ply.subdata(in: 0..<range.upperBound), encoding: .ascii),
              header.contains("golmok-objcap") else {
            eprint("golmok-objcap colmap: \(args[2]) is not a pointcloud.ply written by golmok-objcap")
            return 2
        }
        let body = ply.subdata(in: range.upperBound..<ply.count)
        let n = body.count / 16
        body.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
            for i in 0..<n {
                let o = i * 16
                let x = Float(bitPattern: UInt32(littleEndian: raw.loadUnaligned(fromByteOffset: o, as: UInt32.self)))
                let y = Float(bitPattern: UInt32(littleEndian: raw.loadUnaligned(fromByteOffset: o + 4, as: UInt32.self)))
                let z = Float(bitPattern: UInt32(littleEndian: raw.loadUnaligned(fromByteOffset: o + 8, as: UInt32.self)))
                let r = raw[o + 12], g = raw[o + 13], b = raw[o + 14]
                points += "\(i + 1) \(x) \(y) \(z) \(r) \(g) \(b) 0\n"
            }
        }
        pointCount = n
    }
    do {
        try FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
        try cameras.write(to: outDir.appendingPathComponent("cameras.txt"), atomically: true, encoding: .utf8)
        try images.write(to: outDir.appendingPathComponent("images.txt"), atomically: true, encoding: .utf8)
        try points.write(to: outDir.appendingPathComponent("points3D.txt"), atomically: true, encoding: .utf8)
    } catch {
        eprint("golmok-objcap colmap: write failed: \(error)")
        return 1
    }
    eprint("golmok-objcap colmap: \(written) images, \(pointCount) points -> \(outDir.path) (EXPERIMENTAL)")
    eprint(String(format: "golmok-objcap colmap: lens distortion NOT applied; max |relative radial magnification| in the LUTs = %.5f", maxMag))
    return written > 0 ? 0 : 1
}
