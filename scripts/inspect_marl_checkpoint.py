#!/usr/bin/env python3
"""Inspect and validate a WKR MARL checkpoint before proof experiments."""
import argparse
import sys
from pathlib import Path


EXPECTED_OBSERVATION_DIM = 12
EXPECTED_ACTION_DIM = 6
COMPATIBLE_MODEL_TYPES = {'qmix', 'marl_decpomdp'}


def load_checkpoint(path: Path):
    import torch
    return torch.load(str(path), map_location='cpu', weights_only=False)


def metadata_from(checkpoint):
    return checkpoint.get('metadata') or {} if isinstance(checkpoint, dict) else {}


def state_dict_from(checkpoint):
    if isinstance(checkpoint, dict):
        return checkpoint.get('state_dict') or checkpoint.get('model_state_dict')
    return checkpoint


def check_state_dict_shapes(state_dict):
    errors = []
    if not isinstance(state_dict, dict):
        return ['checkpoint does not contain a PyTorch state_dict']
    fc1 = state_dict.get('fc1.weight')
    fc3 = state_dict.get('fc3.weight')
    if fc1 is None:
        errors.append('state_dict is missing fc1.weight')
    elif len(fc1.shape) != 2 or int(fc1.shape[1]) != EXPECTED_OBSERVATION_DIM:
        errors.append(f'fc1.weight expects observation_dim {EXPECTED_OBSERVATION_DIM}, got shape {tuple(fc1.shape)}')
    if fc3 is None:
        errors.append('state_dict is missing fc3.weight')
    elif len(fc3.shape) != 2 or int(fc3.shape[0]) != EXPECTED_ACTION_DIM:
        errors.append(f'fc3.weight expects action_dim {EXPECTED_ACTION_DIM}, got shape {tuple(fc3.shape)}')
    return errors


def validate(path: Path, require_proof: bool):
    errors = []
    if not path.exists():
        return {'errors': [f'checkpoint file does not exist: {path}'], 'metadata': {}}
    try:
        checkpoint = load_checkpoint(path)
    except Exception as exc:
        return {'errors': [f'torch.load failed: {exc}'], 'metadata': {}}

    metadata = metadata_from(checkpoint)
    state_dict = state_dict_from(checkpoint)
    errors.extend(check_state_dict_shapes(state_dict))

    model_type = metadata.get('model_type')
    if require_proof:
        if model_type not in COMPATIBLE_MODEL_TYPES:
            errors.append(f'metadata.model_type must be one of {sorted(COMPATIBLE_MODEL_TYPES)}, got {model_type!r}')
        if metadata.get('trained') is not True:
            errors.append('metadata.trained must be true')
        if metadata.get('allowed_for_wkr_proof') is not True:
            errors.append('metadata.allowed_for_wkr_proof must be true')
        if metadata.get('num_agents') != 8:
            errors.append(f'metadata.num_agents must be 8, got {metadata.get("num_agents")!r}')
        if metadata.get('observation_dim') != EXPECTED_OBSERVATION_DIM:
            errors.append(f'metadata.observation_dim must be {EXPECTED_OBSERVATION_DIM}, got {metadata.get("observation_dim")!r}')
        if metadata.get('action_dim') != EXPECTED_ACTION_DIM:
            errors.append(f'metadata.action_dim must be {EXPECTED_ACTION_DIM}, got {metadata.get("action_dim")!r}')
        scenarios = metadata.get('training_scenarios')
        if scenarios != ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']:
            errors.append(f'metadata.training_scenarios must be S1-S6, got {scenarios!r}')
        if metadata.get('training_env') not in {'headless_fast_kinematic', 'gazebo_headless'}:
            errors.append(f'metadata.training_env is unsupported: {metadata.get("training_env")!r}')

    return {'errors': errors, 'metadata': metadata}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--require-proof', action='store_true')
    args = parser.parse_args()

    result = validate(Path(args.model), args.require_proof)
    metadata = result['metadata']
    print(f'model: {args.model}')
    for key in ['model_type', 'trained', 'allowed_for_wkr_proof', 'training_env', 'training_scenarios', 'num_agents', 'observation_dim', 'action_dim', 'created_at', 'git_commit']:
        print(f'{key}: {metadata.get(key)}')
    if result['errors']:
        print('Validation failed:')
        for error in result['errors']:
            print(f'  - {error}')
        return 1
    print('Validation passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
