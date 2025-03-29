#!/usr/bin/env python3
"""
CDK Deployment Script

This script helps deploy the AI Multi-Communications Engine infrastructure.
It sets up the required environment and runs CDK commands with appropriate
parameters.
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import dotenv for loading environment variables
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def run_command(command, verbose=False):
    """Run a shell command and optionally print output."""
    if verbose:
        print(f"Running: {command}")
    
    process = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=not verbose,
    )
    
    if process.returncode != 0:
        if not verbose:
            print(f"Command failed: {command}")
            print(f"STDOUT: {process.stdout}")
            print(f"STDERR: {process.stderr}")
        sys.exit(process.returncode)
    
    return process.stdout


def deploy_stack(stack_name=None, all_stacks=False, verbose=False):
    """Deploy CDK stack(s)."""
    cdk_cmd = "cdk deploy"
    
    if all_stacks:
        cdk_cmd += " --all"
    elif stack_name:
        cdk_cmd += f" {stack_name}"
    
    cdk_cmd += " --require-approval never"
    
    run_command(cdk_cmd, verbose=verbose)


def destroy_stack(stack_name=None, all_stacks=False, verbose=False):
    """Destroy CDK stack(s)."""
    cdk_cmd = "cdk destroy"
    
    if all_stacks:
        cdk_cmd += " --all"
    elif stack_name:
        cdk_cmd += f" {stack_name}"
    
    cdk_cmd += " --force"
    
    run_command(cdk_cmd, verbose=verbose)


def list_stacks(verbose=False):
    """List available CDK stacks."""
    output = run_command("cdk list", verbose=verbose)
    
    if not verbose:
        print("Available stacks:")
        for line in output.strip().split("\n"):
            print(f"  - {line}")


def main():
    parser = argparse.ArgumentParser(description="Deploy AI Multi-Communications Engine infrastructure")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy CDK stack(s)")
    deploy_parser.add_argument("--stack", help="Stack name to deploy")
    deploy_parser.add_argument("--all", action="store_true", help="Deploy all stacks")
    
    # Destroy command
    destroy_parser = subparsers.add_parser("destroy", help="Destroy CDK stack(s)")
    destroy_parser.add_argument("--stack", help="Stack name to destroy")
    destroy_parser.add_argument("--all", action="store_true", help="Destroy all stacks")
    
    # List command
    subparsers.add_parser("list", help="List available stacks")
    
    # Synth command
    subparsers.add_parser("synth", help="Synthesize CloudFormation template")
    
    # Common arguments
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Print current environment
    if args.verbose:
        print(f"AWS_REGION: {os.environ.get('AWS_REGION', 'Not set')}")
        print(f"AWS_PROFILE: {os.environ.get('AWS_PROFILE', 'Not set')}")
    
    # Execute the appropriate command
    if args.command == "deploy":
        deploy_stack(args.stack, args.all, args.verbose)
    elif args.command == "destroy":
        destroy_stack(args.stack, args.all, args.verbose)
    elif args.command == "list":
        list_stacks(args.verbose)
    elif args.command == "synth":
        run_command("cdk synth", args.verbose)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 