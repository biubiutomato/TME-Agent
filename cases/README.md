## 📁 Case Study Inputs

The `cases/` folder contains the input user utterances for four multi-turn interactive scenarios used in our TME paper:

- **v2**: Spatial memory system with rollback, replacement, DAG dependencies, and memory-aware QA  
  ↪︎ Paper: [*Task Memory Engine: Spatial Memory for Robust Multi-Step LLM Agents*](https://arxiv.org/abs/2505.19436)
```bibtex
@misc{ye2025taskmemoryenginespatial,
      title={Task Memory Engine: Spatial Memory for Robust Multi-Step LLM Agents}, 
      author={Ye Ye},
      year={2025},
      eprint={2505.19436},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2505.19436}, 
}
```

**Run Commands**:

```bash
# Run with default classifier (general)
python run_case.py cases/trip_planning_case.json
python run_case.py cases/cooking_case.json
python run_case.py cases/meeting_scheduling_case.json

# Run cart case with specialized intent_classifier
python run_case.py cases/cart_editing_case.json --mode cart
```

- `trip_planning_case.json` – Revisions, checks, and flight planning.
- `cooking_case.json` – Shared ingredient substitutions across tasks.
- `meeting_scheduling_case.json` – Participant conflicts and meeting consolidation.
- `cart_editing_case.json` – Sequential add/remove/reset operations.

Each JSON file is a list of user utterances that simulate one full task interaction session.

> Note: Future versions will restructure these into subfolders per case to include outputs, parsed graphs, and evaluation annotations.

