"""Export ORM metadata as a Jira-ready PNG and editable dbdiagram DBML."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.models import Base

OUTPUT = Path(__file__).resolve().parents[2] / "docs"
POSITIONS = {
    "users": (70, 170),
    "library_entries": (880, 170),
    "watched_episodes": (1690, 170),
    "media_titles": (70, 870),
    "seasons": (880, 870),
    "episodes": (1690, 870),
}
WIDTH = 720
ROW = 36


def column_type(column) -> str:
    value = str(column.type.compile(dialect=postgresql.dialect())).lower()
    return value.replace("timestamp with time zone", "timestamptz")


def export_dbml() -> str:
    lines = [
        "// Generated from app.models; regenerate with python -m app.export_schema",
        "",
    ]
    for table in Base.metadata.sorted_tables:
        lines.append(f"Table {table.name} {{")
        for column in table.columns:
            flags = ["null" if column.nullable else "not null"]
            if column.primary_key and len(table.primary_key.columns) == 1:
                flags.append("pk")
            if column.server_default is not None:
                flags.append(f"default: `{column.server_default.arg}`")
            lines.append(f"  {column.name} {column_type(column)} [{', '.join(flags)}]")
        indexes = []
        if len(table.primary_key.columns) > 1:
            indexes.append(
                f"({', '.join(c.name for c in table.primary_key.columns)}) [pk]"
            )
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                indexes.append(
                    f"({', '.join(c.name for c in constraint.columns)}) [unique]"
                )
        for index in sorted(table.indexes, key=lambda item: item.name):
            expressions = ", ".join(
                expression.name
                if hasattr(expression, "name") and not hasattr(expression, "clauses")
                else f"`{expression.compile(dialect=postgresql.dialect(), compile_kwargs={'include_table': False})}`"
                for expression in index.expressions
            )
            indexes.append(f"({expressions})" + (" [unique]" if index.unique else ""))
        if indexes:
            lines.extend(
                ["  indexes {", *(f"    {index}" for index in sorted(indexes)), "  }"]
            )
        checks = sorted(
            str(c.sqltext) for c in table.constraints if hasattr(c, "sqltext")
        )
        if checks:
            lines.extend(["  checks {", *(f"    `{check}`" for check in checks), "  }"])
        lines.extend(["}", ""])
    for table in Base.metadata.sorted_tables:
        for fk in sorted(table.foreign_keys, key=lambda key: key.parent.name):
            lines.append(
                f"Ref: {table.name}.{fk.parent.name} > "
                f"{fk.target_fullname} [delete: {fk.ondelete.lower()}]"
            )
    return "\n".join(lines) + "\n"


def export_png(path: Path) -> None:
    image = Image.new("RGB", (2480, 1570), "#f1f5f9")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=23)
    small = ImageFont.load_default(size=20)
    heading = ImageFont.load_default(size=38)
    draw.text((70, 40), "MediaTrack | PostgreSQL schema", fill="#0f172a", font=heading)
    draw.text(
        (70, 100),
        "6 tables | PK = primary key | FK = foreign key | NULL = optional | NN = required",
        fill="#475569",
        font=font,
    )

    def height(name):
        return 100 + ROW * len(Base.metadata.tables[name].columns)

    def link(points, label):
        draw.line(points, fill="#64748b", width=4)
        x, y = points[-1]
        px, py = points[-2]
        dx, dy = (
            (1 if x > px else -1) if x != px else 0,
            (1 if y > py else -1) if y != py else 0,
        )
        draw.polygon(
            [
                (x, y),
                (x - dx * 16 + dy * 8, y - dy * 16 + dx * 8),
                (x - dx * 16 - dy * 8, y - dy * 16 - dx * 8),
            ],
            fill="#64748b",
        )
        first, second = points[0], points[1]
        mx, my = (first[0] + second[0]) // 2, (first[1] + second[1]) // 2
        draw.text((mx - 17, my - 32), label, font=small, fill="#475569")

    link([(790, 320), (880, 320)], "1:N")
    link([(1600, 320), (1690, 320)], "1:N")
    link(
        [(430, 870), (430, 770), (1240, 770), (1240, 170 + height("library_entries"))],
        "1:N",
    )
    link([(790, 1030), (880, 1030)], "1:N")
    link([(1600, 1030), (1690, 1030)], "1:N")
    link([(2050, 870), (2050, 170 + height("watched_episodes"))], "1:N")

    for name, (x, y) in POSITIONS.items():
        table = Base.metadata.tables[name]
        draw.rounded_rectangle(
            (x, y, x + WIDTH, y + height(name)),
            radius=12,
            fill="white",
            outline="#cbd5e1",
            width=2,
        )
        draw.rounded_rectangle((x, y, x + WIDTH, y + 60), radius=12, fill="#1e3a5f")
        draw.text((x + 22, y + 16), name, font=font, fill="white")
        # Keep inherited IDs first for a consistent visual reading order.
        columns = sorted(table.columns, key=lambda column: column.name != "id")
        for number, column in enumerate(columns):
            cy = y + 76 + number * ROW
            flags = "/".join(
                flag
                for flag, enabled in (
                    ("PK", column.primary_key),
                    ("FK", bool(column.foreign_keys)),
                )
                if enabled
            )
            draw.text((x + 16, cy), flags, font=small, fill="#2563eb")
            draw.text((x + 95, cy), column.name, font=font, fill="#0f172a")
            draw.text((x + 390, cy), column_type(column), font=small, fill="#475569")
            draw.text(
                (x + 645, cy),
                "NULL" if column.nullable else "NN",
                font=small,
                fill="#64748b",
            )
    draw.text(
        (70, 1490),
        "Arrows: parent (1) to children (0..N). FK fields identify each relationship.",
        font=font,
        fill="#475569",
    )
    draw.text(
        (70, 1530),
        "Source: app.models | Full defaults, indexes, checks and deletion rules: database-schema.dbml",
        font=small,
        fill="#475569",
    )
    image.save(path)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "database-schema.dbml").write_text(export_dbml(), encoding="utf-8")
    export_png(OUTPUT / "database-schema.png")
    print("Saved docs/database-schema.png and docs/database-schema.dbml")


if __name__ == "__main__":
    main()
