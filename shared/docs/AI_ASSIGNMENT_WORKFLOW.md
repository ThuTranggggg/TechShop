# AI Assignment Workflow

This repo now includes a single pipeline that generates the assignment artefacts the teacher asks for.

## Run

```bash
python shared/scripts/ai_assignment_pipeline.py all
```

The pipeline writes to:

```text
shared/generated/ai_assignment/
```

## Output files

| File | Use in report |
| --- | --- |
| `aiservice02_report.md` | Final report draft to export as PDF |
| `data_user500.csv` | Main dataset with 500 users |
| `data_user500_preview.csv` | Copy the first 20 rows into the PDF |
| `data_user500_20rows.svg` | Image of 20 rows for the PDF |
| `actions_distribution.svg` | Dataset action distribution plot |
| `profiles_distribution.svg` | Behavior-template distribution plot |
| `rnn_learning_curve.svg` | RNN training plot |
| `lstm_learning_curve.svg` | LSTM training plot |
| `bilstm_learning_curve.svg` | biLSTM training plot |
| `model_comparison.svg` | Compare all 3 models |
| `model_best_confusion_matrix.svg` | Confusion matrix of the chosen model |
| `model_best.pt` | Best trained model checkpoint |
| `training_results.json` | Metrics and selection details |
| `product_catalog.json` | Product metadata used in graph import |
| `behavior_profiles.json` | User-to-behavior mapping for graph import |
| `kb_graph_preview.svg` | KB_Graph image for the report |
| `kb_graph_summary.json` | Graph counts and Neo4j import status |
| `kb_graph_sample_queries.cypher` | Sample Neo4j queries for screenshots |
| `rag_flow.svg` | Image for the RAG chat section |
| `integration_flow.svg` | Image for the e-commerce integration section |

## Notes

- The training step requires `torch` in the active Python environment.
- The graph import tries to connect to Neo4j first.
- If Neo4j is not running locally, the script still generates the preview SVG and query file, then logs a skip message.
- The pipeline is deterministic by seed, so rerunning it should reproduce the same structure.
- To export the report as PDF, open `aiservice02_report.md` in a Markdown renderer or run a converter such as `pandoc`.
