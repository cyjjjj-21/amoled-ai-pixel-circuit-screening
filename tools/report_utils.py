"""Small Markdown table renderer extracted from the previous report framework."""


def markdown_table(rows, columns):
    lines = ["| " + " | ".join(label for _, label in columns) + " |",
             "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        values = []
        for field, _ in columns:
            value = row.get(field, "")
            if isinstance(value, float):
                value = f"{value:.3f}"
            values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return lines
