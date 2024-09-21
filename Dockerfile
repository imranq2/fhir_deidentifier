# First stage: Build the .NET code
FROM mcr.microsoft.com/dotnet/sdk:6.0 AS build

# Install git
#RUN apt-get update && apt-get install -y git

# Install wget (if not already available)
RUN apt-get update && apt-get install -y wget

# Clone the GitHub repository
#RUN git clone https://github.com/microsoft/Tools-for-Health-Data-Anonymization.git app

# Download the source tar.gz from the GitHub releases page
RUN wget https://github.com/microsoft/Tools-for-Health-Data-Anonymization/archive/refs/tags/v3.1.1.tar.gz -O source.tar.gz

# Extract the tar.gz file and then remove the archive to clean up
RUN tar -xzf source.tar.gz && rm source.tar.gz

RUN mv Tools-for-Health-Data-Anonymization-3.1.1 app

WORKDIR /app

RUN ls -halt .

RUN ls -haltR FHIR/src/
# Copy the project files
#COPY . .

# Build the project
RUN dotnet build FHIR/src/Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool -c Release

# Second stage: Set up the runtime environment for .NET, Mono (v6.12+), and Python
FROM mcr.microsoft.com/dotnet/runtime:6.0

# Install Python, pip, pythonnet, and Mono
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install pythonnet>=3.0.4 fastapi uvicorn

WORKDIR /app

ENV PYTHONPATH=/app;/lib/netlib

COPY --from=build /app/FHIR/src/Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool/bin/Release/net6.0 /lib/netlib

RUN ls -halt /lib/netlib

ENV PYTHONNET_RUNTIME=coreclr
#ENTRYPOINT ["dotnet", "Microsoft.Health.Fhir.Anonymizer.R4.CommandLineTool.dll"]

# Copy the FastAPI Python code
COPY ./fastapi-app /app/fastapi-app

# Expose the FastAPI port
EXPOSE 8000

# Command to run FastAPI
CMD ["uvicorn", "fastapi-app.main:app", "--host", "0.0.0.0", "--port", "8000"]
