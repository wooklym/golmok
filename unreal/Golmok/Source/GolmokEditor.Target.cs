using UnrealBuildTool;

public class GolmokEditorTarget : TargetRules
{
	public GolmokEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("Golmok");
	}
}
