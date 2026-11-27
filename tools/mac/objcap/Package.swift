// swift-tools-version:5.9
// golmok-objcap: Apple Object Capture (RealityKit PhotogrammetrySession) command-line wrapper.
// WP-21 candidate Mac replacement for the RealityScan mesh step (D-005, D-022). No package dependencies.
import PackageDescription

let package = Package(
    name: "golmok-objcap",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "golmok-objcap",
            path: "Sources/golmok-objcap",
            linkerSettings: [.linkedFramework("RealityKit")]
        ),
    ]
)
