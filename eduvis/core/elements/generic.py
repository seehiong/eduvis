"""Generic element specs — available for all subjects."""

from ..registry import ElementSpec, FieldSpec

ELEMENT_SPECS: list[ElementSpec] = [
    ElementSpec(
        name="text_list",
        subjects=["*"],
        synopsis="items: [strings]  (optional color per item)",
        fields=[
            FieldSpec("items", type="array", required=True,
                      description="List of bullet strings; prefix 'no-bullet:' to suppress bullet"),
            FieldSpec("color", type="color", required=False,
                      description="Override bullet color for all items"),
            FieldSpec("anchor", type="string", required=False, default="start",
                      enum=["start", "middle", "center"],
                      description="Text alignment"),
        ],
    ),
    ElementSpec(
        name="fact_boxes",
        subjects=["*"],
        synopsis="items: [{text, border_color}]",
        fields=[
            FieldSpec("items", type="array", required=True,
                      description="List of fact box dicts",
                      items=FieldSpec("item", type="object", properties=[
                          FieldSpec("text", type="string", description="Fact box content"),
                          FieldSpec("border_color", type="color", required=False,
                                    description="Box border colour"),
                      ])),
        ],
    ),
    ElementSpec(
        name="example_panel",
        subjects=["*"],
        synopsis="items: [{heading, body}]  — side-by-side comparison panels",
        fields=[
            FieldSpec("items", type="array", required=True,
                      description="List of panel dicts (max 3 for readability)",
                      items=FieldSpec("item", type="object", properties=[
                          FieldSpec("heading", type="string", description="Bold panel title"),
                          FieldSpec("body", type="string",
                                    description="Panel body; use \\n for explicit line breaks"),
                      ])),
        ],
    ),
    ElementSpec(
        name="callout_box",
        subjects=["*"],
        synopsis="title, lines: [strings], border_color — highlighted callout",
        fields=[
            FieldSpec("title", type="string", required=False, description="Bold callout heading"),
            FieldSpec("lines", type="array", required=True, description="Body text lines"),
            FieldSpec("border_color", type="color", required=False, default="cyan"),
        ],
    ),
    ElementSpec(
        name="summary_list",
        subjects=["*"],
        synopsis="items: [strings]  — identical to text_list, use on summary/takeaway slides",
        fields=[
            FieldSpec("items", type="array", required=True, description="Summary bullet strings"),
        ],
        notes=["PREFER summary_list on final slides to signal lesson wrap-up."],
    ),
    ElementSpec(
        name="multiple_choice",
        subjects=["*"],
        synopsis="question: string, options: {A, B, C, D}  — MCQ layout",
        fields=[
            FieldSpec("question", type="string", required=True, description="The MCQ stem"),
            FieldSpec("options", type="object", required=True,
                      description="Exactly four options keyed A–D",
                      properties=[
                          FieldSpec("A", type="string"),
                          FieldSpec("B", type="string"),
                          FieldSpec("C", type="string"),
                          FieldSpec("D", type="string"),
                      ]),
        ],
    ),
    ElementSpec(
        name="hint_list",
        subjects=["*"],
        synopsis="items: [strings], final: string  — numbered hints",
        fields=[
            FieldSpec("items", type="array", required=True,
                      description="Hint steps (auto-numbered unless item starts with a digit or 'Step')"),
            FieldSpec("final", type="string", required=False,
                      description="Confirmation method shown in a box at the bottom"),
        ],
    ),
    ElementSpec(
        name="number_line",
        subjects=["*"],
        synopsis="range: [min, max], highlight: [{value, label, color}]  — annotated number line",
        fields=[
            FieldSpec("range", type="array", required=True,
                      description="[min, max] numeric bounds"),
            FieldSpec("highlight", type="array", required=False,
                      description="List of {value, label, color} highlight markers",
                      items=FieldSpec("hl", type="object", properties=[
                          FieldSpec("value", type="number", description="Position on the line"),
                          FieldSpec("label", type="string", required=False),
                          FieldSpec("color", type="color", required=False),
                          FieldSpec("type", type="string", required=False,
                                    enum=["jump"],
                                    description="'jump' draws a curved hop arrow"),
                      ])),
            FieldSpec("direction_labels", type="object", required=False,
                      description="{left: 'Smaller', right: 'Larger'} axis end labels",
                      properties=[
                          FieldSpec("left", type="string", required=False),
                          FieldSpec("right", type="string", required=False),
                      ]),
            FieldSpec("caption", type="string", required=False,
                      description="Title above the line"),
        ],
    ),
    ElementSpec(
        name="mixed_card",
        subjects=["*"],
        synopsis="ribbon_type: solve|remember|review, ribbon_label: string, items: [{type: text|math_grid, ...}] — mixed card",
        fields=[
            FieldSpec("ribbon_type", type="string", required=False, default="solve",
                      enum=["solve", "remember", "review"]),
            FieldSpec("ribbon_label", type="string", required=False),
            FieldSpec("items", type="array", required=True,
                      description="List of sub-elements to render within the card",
                      items=FieldSpec("item", type="object", properties=[
                          FieldSpec("type", type="string", required=True, enum=["text", "math_grid"]),
                          FieldSpec("lines", type="array", required=False),
                          FieldSpec("mode", type="string", required=False),
                          FieldSpec("rows", type="array", required=False),
                          FieldSpec("headers", type="array", required=False),
                          FieldSpec("row_colors", type="array", required=False),
                      ])),
        ],
    ),
]
