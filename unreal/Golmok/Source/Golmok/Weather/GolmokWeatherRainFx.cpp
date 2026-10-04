#include "Weather/GolmokWeatherRainFx.h"

#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/PackageName.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraTypes.h"
#include "UObject/SoftObjectPath.h"
#include "Weather/GolmokWeatherMath.h"

// The only file of the module that includes Niagara headers (design section 1; test_ue_wp16_fixture.py checks it).
// The component is created by hand (NewObject + SetAsset + RegisterComponent) instead of UNiagaraFunctionLibrary so
// the actor, its name and its flags stay ours [미확인 §17 #3].

namespace GolmokWeatherRainFx
{
	namespace Private
	{
		const TCHAR* ActorName = TEXT("GolmokWeatherFx");

		UNiagaraComponent* Component(const AActor* FxActor)
		{
			return IsValid(FxActor) ? Cast<UNiagaraComponent>(FxActor->GetRootComponent()) : nullptr;
		}

		/**
		 * Full "User.<name>" names. UNiagaraComponent's override store is a user redirection store, which maps between
		 * the prefixed and the bare name [미확인 §17 #4: Golmok.Weather.Runtime checks the parameters exist].
		 */
		FNiagaraVariable FloatVariable(const char* Name)
		{
			return FNiagaraVariable(FNiagaraTypeDefinition::GetFloatDef(), FName(Name));
		}

		FNiagaraVariable VectorVariable(const char* Name)
		{
			return FNiagaraVariable(FNiagaraTypeDefinition::GetVec3Def(), FName(Name));
		}
	} // namespace Private

	AActor* Spawn(UWorld* World, const GolmokWeather::FConfig& Config, ELoad& OutLoad)
	{
		OutLoad = ELoad::Missing;
		if (!Config.bRainFxEnabled)
		{
			OutLoad = ELoad::Disabled;
			return nullptr;
		}
		if (!World)
		{
			return nullptr;
		}
		// Check the package first so an absent asset (clones before V-16, CI) does not log a load failure.
		const FSoftObjectPath Path(Config.RainFxSystem);
		const FString Package = Path.GetLongPackageName();
		UNiagaraSystem* System = nullptr;
		if (Path.IsValid() && !Package.IsEmpty() && FPackageName::DoesPackageExist(Package))
		{
			System = Cast<UNiagaraSystem>(Path.TryLoad());
		}
		if (!System)
		{
			return nullptr;
		}

		FActorSpawnParameters Params;
		Params.Name = FName(Private::ActorName);
		Params.NameMode = FActorSpawnParameters::ESpawnActorNameMode::Requested; // a unique variant if the name is taken
		Params.ObjectFlags |= RF_Transient;                                      // never saved with the level
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		AActor* FxActor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, Params);
		if (!FxActor)
		{
			return nullptr;
		}
		FxActor->SetReplicates(false);
		FxActor->SetCanBeDamaged(false);

		UNiagaraComponent* Rain = NewObject<UNiagaraComponent>(FxActor, TEXT("Rain"), RF_Transient);
		Rain->SetAutoActivate(false);
		Rain->SetAsset(System);
		// World-axis box: the actor never rotates and the component ignores any parent rotation.
		Rain->SetUsingAbsoluteRotation(true);
		FxActor->SetRootComponent(Rain);
		FxActor->AddInstanceComponent(Rain);
		Rain->RegisterComponent();
		WriteBoxHalfExtent(FxActor, Config.BoxHalfExtentCm);
		WriteRain(FxActor, 0.f, 0.f);
		OutLoad = ELoad::Ok;
		return FxActor;
	}

	UFXSystemComponent* GetComponent(const AActor* FxActor)
	{
		return Private::Component(FxActor);
	}

	void Follow(AActor* FxActor, const FVector& Location)
	{
		if (IsValid(FxActor))
		{
			FxActor->SetActorLocation(Location);
		}
	}

	void WriteRain(AActor* FxActor, float RainIntensity, float SpawnRate)
	{
		if (UNiagaraComponent* Rain = Private::Component(FxActor))
		{
			Rain->SetVariableFloat(FName(GolmokWeatherMath::UserRainIntensity), RainIntensity);
			Rain->SetVariableFloat(FName(GolmokWeatherMath::UserSpawnRate), SpawnRate);
		}
	}

	void WriteBoxHalfExtent(AActor* FxActor, const FVector& HalfExtentCm)
	{
		if (UNiagaraComponent* Rain = Private::Component(FxActor))
		{
			Rain->SetVariableVec3(FName(GolmokWeatherMath::UserBoxHalfExtent), HalfExtentCm);
		}
	}

	void SetActive(AActor* FxActor, bool bActive)
	{
		if (UNiagaraComponent* Rain = Private::Component(FxActor))
		{
			if (bActive)
			{
				Rain->Activate(/*bReset*/ true); // [미확인 §17 #12] warmup on re-activation
			}
			else
			{
				Rain->Deactivate();
			}
		}
	}

	bool IsActive(const AActor* FxActor)
	{
		const UNiagaraComponent* Rain = Private::Component(FxActor);
		return Rain && Rain->IsActive();
	}

	void Reset(AActor* FxActor, bool bActive)
	{
		if (UNiagaraComponent* Rain = Private::Component(FxActor))
		{
			if (bActive)
			{
				Rain->ResetSystem();
			}
			else
			{
				Rain->DeactivateImmediate();
			}
		}
	}

	bool ReadUserParameters(const AActor* FxActor, float& OutRainIntensity, float& OutSpawnRate, FVector& OutBoxHalfExtent)
	{
		const UNiagaraComponent* Rain = Private::Component(FxActor);
		if (!Rain)
		{
			return false;
		}
		// [미확인 §17 #4] const GetOverrideParameters / FindParameterOffset / GetParameterValue<T> in 5.8.
		const auto& Store = Rain->GetOverrideParameters(); // the user redirection store (prefixed and bare names)
		const FNiagaraVariable RainVar = Private::FloatVariable(GolmokWeatherMath::UserRainIntensity);
		const FNiagaraVariable SpawnVar = Private::FloatVariable(GolmokWeatherMath::UserSpawnRate);
		const FNiagaraVariable BoxVar = Private::VectorVariable(GolmokWeatherMath::UserBoxHalfExtent);
		if (!Store.FindParameterOffset(RainVar) || !Store.FindParameterOffset(SpawnVar) || !Store.FindParameterOffset(BoxVar))
		{
			return false;
		}
		OutRainIntensity = Store.GetParameterValue<float>(RainVar);
		OutSpawnRate = Store.GetParameterValue<float>(SpawnVar);
		const FVector3f Box = Store.GetParameterValue<FVector3f>(BoxVar);
		OutBoxHalfExtent = FVector(Box);
		return true;
	}

	bool HasUserParameters(const AActor* FxActor)
	{
		const UNiagaraComponent* Rain = Private::Component(FxActor);
		const UNiagaraSystem* System = Rain ? Rain->GetAsset() : nullptr;
		if (!System)
		{
			return false;
		}
		// The asset's exposed (User) store, not the component's override store: SetVariable* adds missing entries there, so
		// only the asset proves NS_GolmokRain declares the contract. [미확인 §17 #4] GetExposedParameters / FindParameterOffset in 5.8.
		const auto& Exposed = System->GetExposedParameters();
		return Exposed.FindParameterOffset(Private::FloatVariable(GolmokWeatherMath::UserRainIntensity)) &&
			Exposed.FindParameterOffset(Private::FloatVariable(GolmokWeatherMath::UserSpawnRate)) &&
			Exposed.FindParameterOffset(Private::VectorVariable(GolmokWeatherMath::UserBoxHalfExtent));
	}

	void Destroy(AActor* FxActor)
	{
		if (IsValid(FxActor))
		{
			FxActor->Destroy();
		}
	}
} // namespace GolmokWeatherRainFx
