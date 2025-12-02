# Template System and Custom Fields

## Core Principle

The system operates on the **"request only what you need"** principle. Instead of always asking the model to generate a full set of fields (summary, participants, quotes, etc.), we analyze which templates will be used and request from the model only the data actually needed for those templates.

## How It Works

### 1. Defining Fields in Templates

Each template can define which fields it needs via YAML Front Matter:

```yaml
---
custom_fields:
  participants:
    description: "List of real names of participants"
    structure: ["string"]
  summary:
    description: "A concise executive summary"
    structure: "string"
---
```

### 2. Collecting Fields from All Templates

In `RefineStage`, the following happens:

```python
custom_schema_fields = {}

for artifact_config in job.configuration.output.artifacts:
    plugin_name = artifact_config.plugin
    template_name = artifact_config.template
    
    # Load template
    content, _ = load_template(plugin_name, template_name)
    if content:
        metadata, _ = parse_template(content)
        if "custom_fields" in metadata:
            # MERGE fields from this template with the common set
            custom_schema_fields.update(metadata["custom_fields"])
```

**Key point**: `update()` is used, which means:
- If the `participants` field is needed in **three different templates**, it will be added to the common schema only once
- The resulting `custom_schema_fields` contains a **union** of all fields from all templates

### 3. Forming a Single Request

After collecting all fields, they are passed to `GeminiRefinementProvider`:

```python
result = provider.refine(
    input_data, 
    mode, 
    language=detected_language,
    custom_schema=custom_schema_fields  # All fields from all templates
)
```

The provider constructs a JSON Schema with a **single request** to the model, including all necessary fields:

```json
{
  "participants": ["string"],
  "summary": "string",
  "key_takeaways": ["string"],
  "quotes": [{"speaker": "string", "text": "string"}]
}
```

### 4. Model Generates Data Once

The model processes the transcript **once** and returns JSON with **all** requested fields. The result is saved to `enriched_context.json`.

### 5. Using Data in Templates

At the `GenerateStage`, each template is rendered with the same data from `enriched_context.json`. Each template uses only the fields it needs.

## Example Workflow

### Configuration

```yaml
output:
  artifacts:
    - plugin: markdown
      template: summary  # Needs: summary, key_takeaways, participants
    - plugin: markdown
      template: story    # Needs: summary, participants, quotes, clean_text
    - plugin: pdf
      template: modern   # Needs: summary, key_takeaways, action_items
```

### Step 1: Refine - Field Collection

RefineStage iterates through all three templates:

1. `summary.j2` → adds: `summary`, `key_takeaways`, `participants`
2. `story.j2` → adds: `quotes`, `clean_text` (summary and participants already exist)
3. `modern.j2` → adds: `action_items` (summary and key_takeaways already exist)

**Final schema for the model**:
```json
{
  "summary": "string",
  "key_takeaways": ["string"],
  "participants": ["string"],
  "quotes": [{"speaker": "string", "text": "string"}],
  "clean_text": "string",
  "action_items": [{"assignee": "string", "task": "string"}]
}
```

### Step 2: Refine - Single Request to Model

The model receives **one** prompt with this schema and generates **all** this data in a single call.

### Step 3: Generate - Template Rendering

Each template is rendered with the full data set, but uses only the fields it needs:

- `summary.md` → uses `summary`, `key_takeaways`, `participants`
- `story.md` → uses `summary`, `participants`, `quotes`, `clean_text`
- `modern.pdf` → uses `summary`, `key_takeaways`, `action_items`

## Advantages

1. **Efficiency**: The model is called **once** instead of multiple times for different templates
2. **Cost Optimization**: **Only** needed fields are requested. If only the `concise` template is used, which doesn't require `clean_text`, this expensive text is not generated
3. **Consistency**: All templates work with **the same data**, guaranteeing consistency
4. **Flexibility**: Easy to add new templates with new fields without changing code

## Fallback Mechanism

If **no template** has defined `custom_fields` (old templates without Front Matter), the system uses a default schema:

```python
if custom_schema:
    # Use fields from templates
    ...
else:
    # Fallback: generate standard set
    output_schema = {
        "clean_text": "string",
        "summary": "string",
        "key_takeaways": ["string"],
        ...
    }
```

This ensures **backward compatibility** with old templates.

## File Structure

```
amanu/
├── core/
│   └── templates.py          # load_template(), parse_template()
├── pipeline/
│   ├── refine.py             # Collects fields from templates
│   └── generate.py           # Renders templates with data
├── providers/
│   └── gemini.py             # Builds prompt based on custom_schema
└── templates/
    ├── markdown/
    │   ├── default.j2        # With Front Matter
    │   ├── summary.j2        # With Front Matter
    │   └── stats.j2          # With Front Matter + custom fields
    └── pdf/
        └── modern.j2         # With Front Matter
```

## Related Documentation

- **[Features Guide](./features.md)** - Learn about template configuration in the output section
- **[Configuration Guide](./configuration.md)** - Complete reference for `output.artifacts` settings
- **[Architecture Report](./architecture_report.md)** - Understanding the Generate and Refine stages
- **[Documentation Index](./INDEX.md)** - Full documentation sitemap
