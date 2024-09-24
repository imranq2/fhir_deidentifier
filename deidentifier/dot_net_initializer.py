from pythonnet import load
import clr
import sys

class DotNetInitializer:
    @staticmethod
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

        # Import the required namespaces and classes
        # noinspection PyUnresolvedReferences
        from Microsoft.Health.Fhir.Anonymizer.Core import AnonymizerConfigurationManager
        # noinspection PyUnresolvedReferences
        from Microsoft.Health.Fhir.Anonymizer.Core import AnonymizerEngine

        AnonymizerEngine.InitializeFhirPathExtensionSymbols()

    @staticmethod
    def list_assemblies() -> None:
        """
        List all assemblies and types in the current AppDomain

        :return:
        """
        # noinspection PyUnresolvedReferences
        from System import AppDomain
        for assembly in AppDomain.CurrentDomain.GetAssemblies():
            print(f"Assembly: {assembly.FullName}")
            for t in assembly.GetTypes():
                print(f"  Type: {t.FullName}")
