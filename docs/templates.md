# Templates

Templates are pre-configured governance profiles for specific industries. They bundle validators, thresholds, evaluation sets, and collection sources into a single loadable package.

## Loading a Template

```python
from aegis.templates import load_template

tpl = load_template("hse")
```

A `TemplateConfig` contains:

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Template identifier |
| `config_data` | `dict` | YAML configuration data |
| `validators` | `list[BaseValidator]` | Pre-configured guard validators |
| `sources` | `dict` | Collection source definitions |
| `golden_set` | `dict` | Evaluation test cases |
| `regulations` | `list[dict]` | Regulatory references |

## Available Templates

```python
from aegis.templates import available_templates
print(available_templates())  # ['hse']
```

---

## HSE Template

**Health, Safety & Environment** — calibrated for occupational safety agents in Quebec/Canadian regulatory context.

### Configuration Highlights

- **Guard level**: N4 (kill) for safety-critical assertions
- **Faithfulness threshold**: 97%
- **Autonomy mode**: semi-auto
- **Modules**: observe, guard, evaluate, collect, remember, predict

### Validators

| Validator | Level | Detects |
|-----------|-------|---------|
| `SSTFactCheck` | N4 | "100% safe", "no risk", "skip procedure", PPE dismissal |
| `EPIValidator` | N3 | Missing PPE for detected hazard context (construction, welding, chemicals, height, noise, confined space, asbestos) |
| `CNESSTCompliance` | N3 | Regulatory topics without CNESST/RSST references |
| `HazardMinimizer` | N4 | Severity downplay, worry dismissal, risk trivialization |

### Regulatory References

- ISO 45001 — Occupational health and safety management
- OSHA 1910/1926 — US General/Construction Industry Standards
- CNESST RSST — Quebec safety regulation
- CNESST CSTC — Quebec construction safety code
- Loi 25 — Quebec privacy legislation
- EU AI Act — European AI regulation

### Collection Sources

| Source | Domain | Confidence | Frequency |
|--------|--------|------------|-----------|
| CNESST | cnesst.gouv.qc.ca | 0.95 | 24h |
| IRSST | irsst.qc.ca | 0.90 | 48h |
| APSAM | apsam.com | 0.85 | 48h |
| CCHST | cchst.ca | 0.90 | 48h |
| ISO | iso.org | 0.95 | 168h |
| OSHA | osha.gov | 0.90 | 72h |

### Golden Set

20 test cases (10 passing, 10 failing) covering:

- PPE recommendations (construction, welding, chemicals)
- Confined space entry procedures
- Height work and fall protection
- Hazardous materials handling (asbestos, chemicals)
- Noise protection
- Regulatory compliance (right to refuse, incident reporting, prevention programs)

---

## Creating a Custom Template

Templates follow a standard directory layout:

```
src/aegis/templates/your_template/
├── __init__.py
├── your_template_config.yaml
├── your_template_validators.py
├── your_template_eval_golden_set.json
└── your_template_collect_sources.yaml
```

### Step 1: Create the directory

```bash
mkdir -p src/aegis/templates/finance/
```

### Step 2: Write the configuration YAML

```yaml
# finance_config.yaml
workspace: finance-default
modules: [observe, guard, evaluate]
autonomy: semi-auto

guard:
  level: N3
  pipeline:
    - pii-detector
    - compliance-checker

evaluate:
  faithfulness_threshold: 0.95
```

### Step 3: Implement validators

```python
# finance_validators.py
from aegis.guard.validators import BaseValidator
from aegis.core.guard_levels import GuardLevel, GuardResult

class ComplianceChecker(BaseValidator):
    def __init__(self):
        super().__init__(name="compliance-checker", level=GuardLevel.N3)

    def validate(self, content, *, context=None):
        # your validation logic
        return GuardResult(passed=True, level=self.level, rule=self.name)
```

### Step 4: Register in the loader

Add your template to `_load_validators()` in `src/aegis/templates/loader.py`.

### Step 5: Create golden set and sources

Follow the JSON/YAML format from the HSE template.
