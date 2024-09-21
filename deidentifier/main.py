import json
from typing import Dict, Any

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

    # noinspection PyUnresolvedReferences
    clr.AddReference("/lib/netlib/Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool")
    # noinspection PyUnresolvedReferences
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

@app.post("/anonymize")
async def anonymize(config: Dict[str, Any], resource: Dict[str,Any]):
    try:
        assert config
        assert isinstance(config, dict)
        assert resource
        assert isinstance(resource, dict)
        config_json = json.dumps(config)
        json_content = json.dumps(resource)
        anonymizer_configuration_manager = AnonymizerConfigurationManager.CreateFromSettingsInJson(config_json)
        result: str = AnonymizerEngine(anonymizer_configuration_manager).AnonymizeJson(json_content)
        print(result)

        return json.loads(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "Healthy"}
