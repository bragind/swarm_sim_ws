#!/usr/bin/env python3
"""Create a small MARL checkpoint only for pipeline integration testing."""
import argparse
from pathlib import Path

import torch
import torch.nn as nn


class MARLAgent(nn.Module):
    def __init__(self, state_dim=12, action_dim=6, hidden_dim=128):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, action_dim)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='models/marl/test_policy.pt')
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    model = MARLAgent()
    torch.save({
        'state_dict': model.state_dict(),
        'metadata': {
            'model_type': 'test_integration_checkpoint',
            'trained': False,
            'allowed_for_wkr_proof': False,
        }
    }, out)
    print(f'Created test MARL checkpoint: {out}')


if __name__ == '__main__':
    main()
