using UnrealBuildTool;

public class Golmok : ModuleRules
{
	public Golmok(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// Allow includes relative to the module root, e.g. "Player/GolmokCharacter.h".
		PublicIncludePaths.Add(ModuleDirectory);

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			// WP-04: zone manifest / blockers JSON parsing (FJsonSerializer, FJsonObjectConverter)
			"Json",
			"JsonUtilities"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			// WP-05: RHIGetGPUFrameCycles() for the debug HUD's GPU ms (Debug/GolmokDebugSubsystem.cpp).
			// Remove together with GOLMOK_GPU_TIME_SOURCE if the symbol moved.
			"RHI",
			// WP-05 (PC fix, UE 5.8): GGameThreadTime / GRenderThreadTime live in RenderCore (RenderTimer.h), not Core.
			"RenderCore"
		});

		// Editor-only automation tests (Tests/) start PIE through UnrealEd.
		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.Add("UnrealEd");
		}
	}
}
