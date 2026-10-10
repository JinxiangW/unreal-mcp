#include "Commands/BlueprintGraph/EventManager.h"
#include "Engine/Blueprint.h"
#include "Engine/MemberReference.h"
#include "EdGraph/EdGraph.h"
#include "K2Node_Event.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_FunctionResult.h"
#include "EdGraphSchema_K2.h"
#include "EdGraphSchema_K2_Actions.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "EditorAssetLibrary.h"

namespace
{
	UFunction* GetFirstDeclaredFunction(UFunction* Function)
	{
		while (Function && Function->GetSuperFunction())
		{
			Function = Function->GetSuperFunction();
		}
		return Function;
	}

	UFunction* ResolveCanonicalOverrideFunction(
		UBlueprint* Blueprint,
		const FName OverrideName,
		UClass*& OutDeclaringClass)
	{
		OutDeclaringClass = nullptr;
		if (!Blueprint)
		{
			return nullptr;
		}

		// Never resolve against this Blueprint's generated/skeleton class. Once an override has
		// compiled those classes contain a local UFunction copy, which is not the declaration.
		UFunction* Function = Blueprint->ParentClass
			? Blueprint->ParentClass->FindFunctionByName(OverrideName)
			: nullptr;
		if (!Function)
		{
			Function = FBlueprintEditorUtils::GetInterfaceFunction(Blueprint, OverrideName);
		}

		Function = GetFirstDeclaredFunction(Function);
		if (Function)
		{
			OutDeclaringClass = Function->GetOwnerClass()->GetAuthoritativeClass();
		}
		return Function;
	}

	bool ReferencesCanonicalFunction(
		const FMemberReference& Reference,
		UClass* SelfClass,
		const UFunction* CanonicalFunction)
	{
		if (!CanonicalFunction)
		{
			return false;
		}

		// Native editor-created override nodes keep the canonical member name even if their
		// UObject/node display name receives a suffix.
		if (Reference.GetMemberName() == CanonicalFunction->GetFName())
		{
			return true;
		}

		UFunction* ReferencedFunction = Reference.ResolveMember<UFunction>(SelfClass);
		return GetFirstDeclaredFunction(ReferencedFunction) == CanonicalFunction;
	}

	UK2Node_Event* FindExistingOverrideEvent(
		const UBlueprint* Blueprint,
		const UFunction* CanonicalFunction)
	{
		TArray<UK2Node_Event*> Events;
		FBlueprintEditorUtils::GetAllNodesOfClass<UK2Node_Event>(Blueprint, Events);
		for (UK2Node_Event* EventNode : Events)
		{
			if (EventNode && EventNode->bOverrideFunction && ReferencesCanonicalFunction(
				EventNode->EventReference,
				EventNode->GetBlueprintClassFromNode(),
				CanonicalFunction))
			{
				return EventNode;
			}
		}
		return nullptr;
	}

	UEdGraph* FindExistingOverrideFunctionGraph(
		const UBlueprint* Blueprint,
		const UFunction* CanonicalFunction)
	{
		for (UEdGraph* Graph : Blueprint->FunctionGraphs)
		{
			if (!Graph)
			{
				continue;
			}

			if (Graph->GetFName() == CanonicalFunction->GetFName())
			{
				return Graph;
			}

			TArray<UK2Node_FunctionEntry*> EntryNodes;
			Graph->GetNodesOfClass(EntryNodes);
			for (UK2Node_FunctionEntry* EntryNode : EntryNodes)
			{
				if (EntryNode && ReferencesCanonicalFunction(
					EntryNode->FunctionReference,
					EntryNode->GetBlueprintClassFromNode(),
					CanonicalFunction))
				{
					return Graph;
				}
			}
		}
		return nullptr;
	}
}

TSharedPtr<FJsonObject> FEventManager::AddEventNode(const TSharedPtr<FJsonObject>& Params)
{
	// Validate parameters
	if (!Params.IsValid())
	{
		return CreateErrorResponse(TEXT("Invalid parameters"));
	}

	// Get required parameters
	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
	{
		return CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
	}

	FString EventName;
	if (!Params->TryGetStringField(TEXT("event_name"), EventName))
	{
		return CreateErrorResponse(TEXT("Missing 'event_name' parameter"));
	}

	// Get optional position parameters
	FVector2D Position(0.0f, 0.0f);
	double PosX = 0.0, PosY = 0.0;
	if (Params->TryGetNumberField(TEXT("pos_x"), PosX))
	{
		Position.X = static_cast<float>(PosX);
	}
	if (Params->TryGetNumberField(TEXT("pos_y"), PosY))
	{
		Position.Y = static_cast<float>(PosY);
	}

	// Load the Blueprint
	UBlueprint* Blueprint = LoadBlueprint(BlueprintName);
	if (!Blueprint)
	{
		return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
	}

	// Get the event graph (events can only exist in the event graph)
	if (Blueprint->UbergraphPages.Num() == 0)
	{
		return CreateErrorResponse(TEXT("Blueprint has no event graph"));
	}

	UEdGraph* Graph = Blueprint->UbergraphPages[0];
	if (!Graph)
	{
		return CreateErrorResponse(TEXT("Failed to get Blueprint event graph"));
	}

	// Create the event node
	UK2Node_Event* EventNode = CreateEventNode(Graph, EventName, Position);
	if (!EventNode)
	{
		return CreateErrorResponse(FString::Printf(TEXT("Failed to create event node: %s"), *EventName));
	}

	// Notify changes
	Graph->NotifyGraphChanged();
	FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);

	return CreateSuccessResponse(EventNode);
}

TSharedPtr<FJsonObject> FEventManager::CreateBlueprintOverride(const TSharedPtr<FJsonObject>& Params)
{
	if (!Params.IsValid())
	{
		return CreateErrorResponse(TEXT("Invalid parameters"));
	}

	FString BlueprintName;
	if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
	{
		return CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
	}

	FString OverrideName;
	if (!Params->TryGetStringField(TEXT("override_name"), OverrideName) || OverrideName.IsEmpty())
	{
		return CreateErrorResponse(TEXT("Missing 'override_name' parameter"));
	}

	double PosX = 0.0;
	double PosY = 0.0;
	Params->TryGetNumberField(TEXT("pos_x"), PosX);
	Params->TryGetNumberField(TEXT("pos_y"), PosY);
	const FVector2D Position(static_cast<float>(PosX), static_cast<float>(PosY));

	UBlueprint* Blueprint = LoadBlueprint(BlueprintName);
	if (!Blueprint)
	{
		return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
	}

	UClass* DeclaringClass = nullptr;
	UFunction* OverrideFunction = ResolveCanonicalOverrideFunction(
		Blueprint, FName(*OverrideName), DeclaringClass);
	if (!DeclaringClass || !OverrideFunction)
	{
		return CreateErrorResponse(FString::Printf(
			TEXT("Override function not found in Blueprint parent hierarchy: %s"),
			*OverrideName));
	}

	if (!UEdGraphSchema_K2::CanKismetOverrideFunction(OverrideFunction))
	{
		return CreateErrorResponse(FString::Printf(
			TEXT("Function is not Blueprint-overridable: %s::%s"),
			*DeclaringClass->GetPathName(),
			*OverrideName));
	}

	const bool bIsEvent = UEdGraphSchema_K2::FunctionCanBePlacedAsEvent(OverrideFunction);
	if (bIsEvent)
	{
		UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(Blueprint);
		if (!EventGraph)
		{
			return CreateErrorResponse(TEXT("Blueprint has no event graph"));
		}

		if (UK2Node_Event* ExistingNode = FindExistingOverrideEvent(Blueprint, OverrideFunction))
		{
			return CreateOverrideSuccessResponse(
				Blueprint, OverrideFunction, ExistingNode->GetGraph(), ExistingNode, false, true);
		}

		Blueprint->Modify();
		EventGraph->Modify();
		UK2Node_Event* EventNode = FEdGraphSchemaAction_K2NewNode::SpawnNode<UK2Node_Event>(
			EventGraph,
			Position,
			EK2NewNodeFlags::None,
			[OverrideFunction, DeclaringClass](UK2Node_Event* NewNode)
			{
				NewNode->EventReference.SetExternalMember(OverrideFunction->GetFName(), DeclaringClass);
				NewNode->bOverrideFunction = true;
			});
		if (!EventNode)
		{
			return CreateErrorResponse(FString::Printf(
				TEXT("Failed to create event override: %s"), *OverrideName));
		}

		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		return CreateOverrideSuccessResponse(
			Blueprint, OverrideFunction, EventGraph, EventNode, true, true);
	}

	if (UEdGraph* ExistingGraph = FindExistingOverrideFunctionGraph(Blueprint, OverrideFunction))
	{
		return CreateOverrideSuccessResponse(
			Blueprint, OverrideFunction, ExistingGraph, nullptr, false, false);
	}

	Blueprint->Modify();
	UEdGraph* FunctionGraph = FBlueprintEditorUtils::CreateNewGraph(
		Blueprint,
		OverrideFunction->GetFName(),
		UEdGraph::StaticClass(),
		UEdGraphSchema_K2::StaticClass());
	if (!FunctionGraph)
	{
		return CreateErrorResponse(FString::Printf(
			TEXT("Failed to create function graph for override: %s"), *OverrideName));
	}

	FBlueprintEditorUtils::AddFunctionGraph(
		Blueprint,
		FunctionGraph,
		/* bIsUserCreated = */ false,
		DeclaringClass);

	TArray<UK2Node_FunctionEntry*> EntryNodes;
	FunctionGraph->GetNodesOfClass(EntryNodes);
	if (EntryNodes.Num() > 0)
	{
		EntryNodes[0]->NodePosX = static_cast<int32>(Position.X);
		EntryNodes[0]->NodePosY = static_cast<int32>(Position.Y);
	}

	TArray<UK2Node_FunctionResult*> ResultNodes;
	FunctionGraph->GetNodesOfClass(ResultNodes);
	if (ResultNodes.Num() > 0)
	{
		ResultNodes[0]->NodePosX = static_cast<int32>(Position.X) + 400;
		ResultNodes[0]->NodePosY = static_cast<int32>(Position.Y);
	}

	FunctionGraph->NotifyGraphChanged();
	return CreateOverrideSuccessResponse(
		Blueprint, OverrideFunction, FunctionGraph, nullptr, true, false);
}

UK2Node_Event* FEventManager::CreateEventNode(UEdGraph* Graph, const FString& EventName, const FVector2D& Position)
{
	if (!Graph)
	{
		return nullptr;
	}

	UBlueprint* Blueprint = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
	if (!Blueprint)
	{
		return nullptr;
	}

	// Check for existing event node to avoid duplicates
	UK2Node_Event* ExistingNode = FindExistingEventNode(Graph, EventName);
	if (ExistingNode)
	{
		UE_LOG(LogTemp, Display, TEXT("F18: Using existing event node '%s' (ID: %s)"),
			*EventName, *ExistingNode->NodeGuid.ToString());
		return ExistingNode;
	}

	// Create new event node
	UK2Node_Event* EventNode = nullptr;
	UClass* BlueprintClass = Blueprint->GeneratedClass;

	if (!BlueprintClass)
	{
		UE_LOG(LogTemp, Error, TEXT("F18: Blueprint has no generated class"));
		return nullptr;
	}

	UFunction* EventFunction = BlueprintClass->FindFunctionByName(FName(*EventName));

	if (EventFunction)
	{
		EventNode = NewObject<UK2Node_Event>(Graph);
		EventNode->EventReference.SetExternalMember(FName(*EventName), BlueprintClass);
		EventNode->NodePosX = static_cast<int32>(Position.X);
		EventNode->NodePosY = static_cast<int32>(Position.Y);
		Graph->AddNode(EventNode, true);
		EventNode->PostPlacedNewNode();
		EventNode->AllocateDefaultPins();

		UE_LOG(LogTemp, Display, TEXT("F18: Created new event node '%s' (ID: %s)"),
			*EventName, *EventNode->NodeGuid.ToString());
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("F18: Failed to find function for event name: %s"), *EventName);
	}

	return EventNode;
}

UK2Node_Event* FEventManager::FindExistingEventNode(UEdGraph* Graph, const FString& EventName)
{
	if (!Graph)
	{
		return nullptr;
	}

	for (UEdGraphNode* Node : Graph->Nodes)
	{
		UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node);
		if (EventNode && EventNode->EventReference.GetMemberName() == FName(*EventName))
		{
			return EventNode;
		}
	}

	return nullptr;
}

UBlueprint* FEventManager::LoadBlueprint(const FString& BlueprintName)
{
	// Try direct path first
	FString BlueprintPath = BlueprintName;

	// If no path prefix, assume /Game/Blueprints/
	if (!BlueprintPath.StartsWith(TEXT("/")))
	{
		BlueprintPath = TEXT("/Game/Blueprints/") + BlueprintPath;
	}

	// Add .Blueprint suffix if not present
	if (!BlueprintPath.Contains(TEXT(".")))
	{
		BlueprintPath += TEXT(".") + FPaths::GetBaseFilename(BlueprintPath);
	}

	// Try to load the Blueprint
	UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *BlueprintPath);

	// If not found, try with UEditorAssetLibrary
	if (!BP)
	{
		FString AssetPath = BlueprintPath;
		if (UEditorAssetLibrary::DoesAssetExist(AssetPath))
		{
			UObject* Asset = UEditorAssetLibrary::LoadAsset(AssetPath);
			BP = Cast<UBlueprint>(Asset);
		}
	}

	return BP;
}

TSharedPtr<FJsonObject> FEventManager::CreateSuccessResponse(const UK2Node_Event* EventNode)
{
	TSharedPtr<FJsonObject> Response = MakeShareable(new FJsonObject);
	Response->SetBoolField(TEXT("success"), true);
	Response->SetStringField(TEXT("node_id"), EventNode->NodeGuid.ToString());
	Response->SetStringField(TEXT("event_name"), EventNode->EventReference.GetMemberName().ToString());
	Response->SetNumberField(TEXT("pos_x"), EventNode->NodePosX);
	Response->SetNumberField(TEXT("pos_y"), EventNode->NodePosY);
	return Response;
}

TSharedPtr<FJsonObject> FEventManager::CreateOverrideSuccessResponse(
	const UBlueprint* Blueprint,
	const UFunction* OverrideFunction,
	const UEdGraph* Graph,
	const UK2Node_Event* EventNode,
	bool bCreated,
	bool bIsEvent)
{
	TSharedPtr<FJsonObject> Response = MakeShareable(new FJsonObject);
	Response->SetBoolField(TEXT("success"), true);
	Response->SetBoolField(TEXT("created"), bCreated);
	Response->SetStringField(TEXT("kind"), bIsEvent ? TEXT("event") : TEXT("function"));
	Response->SetStringField(TEXT("override_name"), OverrideFunction->GetName());
	Response->SetStringField(TEXT("declaring_class"), OverrideFunction->GetOwnerClass()->GetAuthoritativeClass()->GetPathName());
	Response->SetStringField(TEXT("blueprint_path"), Blueprint->GetPathName());

	if (Graph)
	{
		Response->SetStringField(TEXT("graph_name"), Graph->GetName());
		Response->SetStringField(TEXT("graph_id"), Graph->GraphGuid.ToString());
	}

	if (EventNode)
	{
		Response->SetStringField(TEXT("node_id"), EventNode->NodeGuid.ToString());
	}
	else if (Graph)
	{
		TArray<UK2Node_FunctionEntry*> EntryNodes;
		Graph->GetNodesOfClass(EntryNodes);
		if (EntryNodes.Num() > 0)
		{
			Response->SetStringField(TEXT("node_id"), EntryNodes[0]->NodeGuid.ToString());
			Response->SetStringField(TEXT("entry_node_id"), EntryNodes[0]->NodeGuid.ToString());
		}

		TArray<UK2Node_FunctionResult*> ResultNodes;
		Graph->GetNodesOfClass(ResultNodes);
		if (ResultNodes.Num() > 0)
		{
			Response->SetStringField(TEXT("result_node_id"), ResultNodes[0]->NodeGuid.ToString());
		}
	}

	return Response;
}

TSharedPtr<FJsonObject> FEventManager::CreateErrorResponse(const FString& ErrorMessage)
{
	TSharedPtr<FJsonObject> Response = MakeShareable(new FJsonObject);
	Response->SetBoolField(TEXT("success"), false);
	Response->SetStringField(TEXT("error"), ErrorMessage);
	return Response;
}
