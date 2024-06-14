# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""
Registers trained ML model and shares to an AZure ML workspace.

Lastest update: 14/06/24
"""

import argparse
from pathlib import Path
import os 
import json

import mlflow
from azure.ai.ml import MLClient
from azure.identity import ManagedIdentityCredential

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_name', type=str, help='Name under which model will be registered')
    parser.add_argument('--model_path', type=str, help='Model directory')
    parser.add_argument('--evaluation_output', type=str, help='Path of eval results')
    parser.add_argument(
        "--model_info_output_path", type=str, help="Path to write model info JSON"
    )
    args, _ = parser.parse_known_args()
    print(f'Arguments: {args}')
    return args


def main(args):
    """Loads model, registers it to the model registry then shares to a shared Azure ML registry."""

    with open((Path(args.evaluation_output) / "deploy_flag"), 'rb') as infile:
        deploy_flag = int(infile.read())
        
    mlflow.log_metric("deploy flag", int(deploy_flag))
    deploy_flag=1
    if deploy_flag==1:

        print("Registering ", args.model_name)

        # load model
        model =  mlflow.sklearn.load_model(args.model_path) 

        # log model using mlflow
        mlflow.sklearn.log_model(model, args.model_name)

        # register logged model using mlflow
        run_id = mlflow.active_run().info.run_id
        model_uri = f'runs:/{run_id}/{args.model_name}'
        mlflow_model = mlflow.register_model(model_uri, args.model_name)
        model_version = mlflow_model.version

        # write model info
        print("Writing JSON")
        dict = {"id": "{0}:{1}".format(args.model_name, model_version)}
        output_path = os.path.join(args.model_info_output_path, "model_info.json")
        with open(output_path, "w") as of:
            json.dump(dict, fp=of)
        
        # write model to shared registry
        credential = ManagedIdentityCredential(client_id="") # Managed identity client ID with Azure ML Registry User role applied
        ml_client_workspace = MLClient(credential=credential,
                                       subscription_id = "",
                                       resource_group_name = "",
                                       workspace_name = "")
        ml_client_workspace.models.share(name=args.model_name, 
                                         version=str(model_version), 
                                         registry_name="", 
                                         share_with_name=args.model_name,
                                         share_with_version=str(model_version))

    else:
        print("Model will not be registered!")

if __name__ == "__main__":
    mlflow.start_run()
    args = parse_args()
    lines = [
        f"Model name: {args.model_name}",
        f"Model path: {args.model_path}",
        f"Evaluation output path: {args.evaluation_output}",
    ]
    for line in lines:
        print(line)
    main(args)
    mlflow.end_run()