import asyncio, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
from postulator.adapters.contentful import ContentfulClient

load_dotenv()

USAGE = (
    "Usage: python tools/dump.py entry <entry_id>\n"
    "       python tools/dump.py content_type <content_type_id>\n"
    "       python tools/dump.py content_types\n"
    "       python tools/dump.py fetch_schema"
)

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "schema")


def _validation_summary(validations: list) -> str:
    parts = []
    for v in validations:
        if "in" in v:
            parts.append("one of: " + ", ".join(f"`{x}`" for x in v["in"]))
        elif "regexp" in v:
            msg = v.get("message", "")
            parts.append(f"regexp: `{v['regexp']['pattern']}`" + (f" — {msg}" if msg else ""))
        elif "linkContentType" in v:
            parts.append("links to: " + ", ".join(f"`{x}`" for x in v["linkContentType"]))
        elif "size" in v:
            s = v["size"]
            parts.append(f"size: {s.get('min', '?')}–{s.get('max', '?')}")
        else:
            parts.append(json.dumps(v))
    return "; ".join(parts)


def _field_type(field: dict) -> str:
    t = field["type"]
    if t == "Link":
        return f"Link<{field.get('linkType', '?')}>"
    if t == "Array":
        items = field.get("items", {})
        it = items.get("type", "?")
        if it == "Link":
            return f"Array<Link<{items.get('linkType', '?')}>>"
        return f"Array<{it}>"
    return t


def _content_type_to_md(ct: dict) -> str:
    ct_id = ct["sys"]["id"]
    name = ct.get("name", ct_id)
    description = ct.get("description", "")
    fields = ct.get("fields", [])

    lines = [f"# `{ct_id}` — {name}", ""]
    if description:
        lines += [description, ""]
    lines += [
        f"**Display field:** `{ct.get('displayField', 'n/a')}`",
        "",
        "## Fields",
        "",
        "| Field ID | Type | Required | Default | Validations |",
        "|----------|------|----------|---------|-------------|",
    ]
    for f in fields:
        if f.get("omitted"):
            continue
        fid = f["id"]
        ftype = _field_type(f)
        required = "✓" if f.get("required") else ""
        default = ""
        if "defaultValue" in f:
            dv = f["defaultValue"].get("en-US", "")
            default = f"`{dv}`"
        validations = f.get("validations", [])
        if f.get("type") == "Array":
            validations = validations + f.get("items", {}).get("validations", [])
        val_str = _validation_summary(validations)
        lines.append(f"| `{fid}` | {ftype} | {required} | {default} | {val_str} |")

    return "\n".join(lines) + "\n"


def _index_to_md(content_types: list) -> str:
    lines = [
        "# Contentful Content Types",
        "",
        "Auto-generated. Run `python tools/dump.py fetch_schema` to refresh.",
        "",
        "| ID | Name | Fields |",
        "|----|------|--------|",
    ]
    for ct in sorted(content_types, key=lambda x: x["sys"]["id"]):
        ct_id = ct["sys"]["id"]
        name = ct.get("name", ct_id)
        field_count = len([f for f in ct.get("fields", []) if not f.get("omitted")])
        lines.append(f"| [`{ct_id}`](./{ct_id}.md) | {name} | {field_count} |")
    return "\n".join(lines) + "\n"


async def main(kind: str, id: str | None):
    async with ContentfulClient(
        space_id=os.environ["CONTENTFUL_SPACE_ID"],
        environment="master",
        token=os.environ["CONTENTFUL_TOKEN"],
    ) as client:
        if kind == "entry":
            data = await client.get_entry(id)
            print(json.dumps(data, indent=2))

        elif kind == "content_type":
            data = await client.get_content_type(id)
            print(json.dumps(data, indent=2))

        elif kind == "content_types":
            resp = await client._request("get", f"{client._base_url}/content_types", params={"limit": 200})
            resp.raise_for_status()
            data = [
                {"id": ct["sys"]["id"], "name": ct.get("name"), "fields": [f["id"] for f in ct.get("fields", [])]}
                for ct in resp.json().get("items", [])
            ]
            print(json.dumps(data, indent=2))

        elif kind == "fetch_schema":
            resp = await client._request("get", f"{client._base_url}/content_types", params={"limit": 200})
            resp.raise_for_status()
            content_types = resp.json().get("items", [])

            os.makedirs(SCHEMA_DIR, exist_ok=True)

            for ct in content_types:
                ct_id = ct["sys"]["id"]
                path = os.path.join(SCHEMA_DIR, f"{ct_id}.md")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(_content_type_to_md(ct))
                print(f"  wrote {ct_id}.md")

            index_path = os.path.join(SCHEMA_DIR, "index.md")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(_index_to_md(content_types))
            print(f"  wrote index.md")
            print(f"\nDone. {len(content_types)} content types written to docs/schema/")

        else:
            print(USAGE)
            sys.exit(1)


if len(sys.argv) < 2:
    print(USAGE)
    sys.exit(1)

kind = sys.argv[1]
id = sys.argv[2] if len(sys.argv) > 2 else None
if kind in ("entry", "content_type") and id is None:
    print(USAGE)
    sys.exit(1)

asyncio.run(main(kind, id))
