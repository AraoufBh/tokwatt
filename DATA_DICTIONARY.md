# TokWatt data dictionary (v0.1.0)

All files are UTF-8 CSV with a header row. Empty cell = not reported / not applicable. Energy is always in watt-hours (Wh); 1 Wh = 3,600 J; values reported per 1,000 inferences in kWh equal Wh per inference.

## estimates.csv

| Column | Description |
|---|---|
| `estimate_id` | Stable identifier `TWE####` |
| `source_id` | Original source (→ `sources.csv`) |
| `reported_in` | Source the value was taken from when it is not the original (e.g. a benchmark tabulated in a paper) |
| `task` | Task identifier (→ `tasks.csv`) |
| `prompt_size` | `short`, `medium`, `long` or a scenario label, when the source defines prompt classes |
| `functional_unit` | What one unit of the estimate is, in the source's terms |
| `model`, `provider`, `host` | Model as named in the source, its developer, and the serving platform |
| `model_access` | `proprietary` or `open-weights` |
| `hardware` | Accelerator / system as stated or inferred by the source |
| `tokens_in`, `tokens_out` | Token counts defining the unit, if specified |
| `output_spec` | Resolution, frames, fps, steps and duration for image/video |
| `energy_wh` | Point estimate as reported, converted to Wh |
| `energy_wh_low`, `energy_wh_high` | Interval attached by the source to the same estimate |
| `energy_wh_sd` | Standard deviation, when the source reports mean ± SD |
| `interval_type` | `IQR`, `SD`, `scenario (...)`, `upper bound`, `none`, … |
| `reported_value`, `reported_unit` | Value and unit exactly as published (traceability) |
| `incl_accelerator` | Active accelerator energy counted: `yes` / `no` / `unknown` |
| `incl_host` | Host CPU, DRAM and other server parts: `yes` / `approx` / `no` / `unknown` |
| `incl_idle` | Idle or reserve capacity: `yes` / `partial` / `approx` / `no` / `unknown` |
| `incl_overhead_pue` | Data-centre overhead via PUE: `yes` / `approx` / `no` / `unknown` |
| `incl_embodied` | Hardware manufacturing (life-cycle): `yes` / `no` / `unknown` |
| `method` | `measured`, `measured_gpu_x2_heuristic`, `modeled`, `disclosed`, `estimated_from_tokens`, `lca`, `secondary_report` |
| `harmonization_factor` | Derived. Multiplier to the "server + facility overhead" boundary |
| `energy_wh_harmonized` | Derived. `energy_wh × harmonization_factor` |
| `co2e_g`, `co2e_basis` | Emissions per unit as reported, and accounting basis |
| `water_ml`, `water_scope` | Water per unit as reported, and scope |
| `data_period` | When the underlying data were collected |
| `in_reference_set` | `TRUE` if the row matches its task's reference configuration and feeds `task_defaults.csv` |
| `locator` | Table, figure or section in the source |
| `verification` | `assistant_extracted_needs_human_check` or `human_verified` |
| `notes` | Caveats, inconsistencies in the source, context |

## task_defaults.csv (derived)

`central_wh` = median of harmonized reference-set points. `low_wh` / `high_wh` = min / max over harmonized reported intervals (IQR, stated range, or mean ± SD clipped at 0; a row without an interval contributes its point). `geomean_wh` = geometric mean of the points. `median_all_rows_wh` = median over every row of the task, a sensitivity check on the reference-set choice. `estimate_ids` lists the rows used.

## tasks.csv

`task_id`, `family` (text, agentic, image, video, classic), `label`, `description`, `reference_config` (the rule deciding `in_reference_set`), `in_app`.

## token_factors.csv

Energy per million tokens by token type (`input (fresh)`, `output`, `cache read`, `blended`), with `method` (`derived`, `regression`).

## macro.csv

`indicator` (e.g. `data_centre_electricity`, `data_centre_power_demand`, `ai_optimized_server_electricity`), `region`, `year`, `value` or `value_low`/`value_high`, `unit`, `kind` (`estimate`, `forecast`, `projection`, `company_statement`), `scenario`, `source_id`, `reported_in`, `locator`.

## grid_carbon.csv

`region`, `iso_code` (blank for aggregates), `year` (latest available, ≥ 2022), `carbon_intensity_gco2e_per_kwh` (life-cycle intensity of electricity generation), `source_id`.

## equivalents.csv

`label`, `energy_wh` per `per` unit, `basis` (`reference_value`, `derived`, `physics`, `physics_assumed_power`, `assumption`, `convention`), `source_id`.

## parameters.csv

Harmonization and app parameters: `F_ACCELERATOR_TO_FULL`, `PUE_REF`, `WUE_ONSITE_L_PER_KWH`, `DEFAULT_PRICE_USD_PER_KWH`, `REACTOR_GW`.
