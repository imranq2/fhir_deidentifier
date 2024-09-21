from fastapi import FastAPI, HTTPException
from pythonnet import load
import clr
import os
import sys

app = FastAPI()


def initialize_anonymizer():
    # Add the /app directory to sys.path if needed
    sys.path.append("/app")
    # Load CoreCLR runtime (if using CoreCLR)
    try:
        load("coreclr")
    except Exception as e:
        raise ImportError(
            "Pythonnet could not load CoreCLR. Make sure .NET 6.0+ is installed in the environment.") from e
    # Path to the .NET assembly (ensure this path is correct)
    assembly_path = os.path.join(
        "/lib/netlib",
        "Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool.dll"
    )
    # Check if the DLL exists
    if not os.path.exists(assembly_path):
        raise FileNotFoundError(f"Could not find the .NET assembly at {assembly_path}")
    # Load the .NET assembly
    try:
        clr.AddReference(assembly_path)
    except Exception as e:
        raise ImportError(f"Failed to load .NET assembly: {e}")
    clr.AddReference("/lib/netlib/Microsoft.Health.Fhir.Anonymizer.R4.Core")
    # Inspect the assembly to list all namespaces and classes
    # noinspection PyUnresolvedReferences
    from System import AppDomain
    def list_assemblies():
        for assembly in AppDomain.CurrentDomain.GetAssemblies():
            print(f"Assembly: {assembly.FullName}")
            for t in assembly.GetTypes():
                print(f"  Type: {t.FullName}")
    # list_assemblies()


initialize_anonymizer()

# Import the required namespaces and classes
# noinspection PyUnresolvedReferences
from Microsoft.Health.Fhir.Anonymizer.Core import AnonymizerConfigurationManager
# noinspection PyUnresolvedReferences
from Microsoft.Health.Fhir.Anonymizer.Core import AnonymizerEngine

AnonymizerEngine.InitializeFhirPathExtensionSymbols()

# Program.Main([])

# from Microsoft.Health.Fhir.Anonymizer.Tool import AnonymizationLogic
# # Import the correct namespace and class
# try:
#     from Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool import AnonymizerTool  # Adjust this if needed
# except ImportError as e:
#     raise ImportError(f"Failed to import .NET class: {e}")

@app.post("/anonymize")
async def anonymize(config_json: str, json_content: str):
    try:
        # config_json = """{
        #   "fhirVersion": "R4",
        #   "processingError":"raise",
        #   "fhirPathRules": [
        #     {"path": "nodesByType('Extension')", "method": "redact"},
        #     {"path": "Organization.identifier", "method": "keep"},
        #     {"path": "nodesByType('Address').country", "method": "keep"},
        #     {"path": "Resource.id", "method": "cryptoHash"},
        #     {"path": "nodesByType('Reference').reference", "method": "cryptoHash"},
        #     {"path": "Group.name", "method": "redact"}
        #   ],
        #   "parameters": {
        #     "dateShiftKey": "",
        #     "cryptoHashKey": "",
        #     "encryptKey": "",
        #     "enablePartialAgesForRedact": true
        #   }
        # }"""
        anonymizer_configuration_manager = AnonymizerConfigurationManager.CreateFromSettingsInJson(config_json)
        # json_content = """{
        #   "resourceType": "Patient",
        #   "id": "example",
        #   "name": [
        #     {
        #       "family": "Doe",
        #       "given": ["John"]
        #     }
        #   ],
        #   "gender": "male",
        #   "birthDate": "1974-12-25"
        # }
        # """
        result = AnonymizerEngine(anonymizer_configuration_manager).AnonymizeJson(json_content)
        print(result)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "Healthy"}
