from flask import Flask, request, send_file, jsonify, render_template
import tempfile
import io
import os
import traceback
import pandas as pd
import ezdxf
from shapely.geometry import LineString
from PIL import Image, ImageDraw
from io import BytesIO

app = Flask(__name__)

# We'll keep references to generated files here for /download
csv_io = None
dxf_io = None
jpg_io = None

def dxf_to_jpg(doc):
    """
    Convert the given ezdxf.document object to a centered, zoomed JPG as BytesIO.
    We do NOT re-read from disk or a stream; we work directly with the doc object.
    """
    msp = doc.modelspace()

    # Compute bounding box
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')

    for entity in msp:
        etype = entity.dxftype()
        if etype == 'LINE':
            start, end = entity.dxf.start, entity.dxf.end
            min_x, min_y = min(min_x, start.x, end.x), min(min_y, start.y, end.y)
            max_x, max_y = max(max_x, start.x, end.x), max(max_y, start.y, end.y)
        elif etype == 'LWPOLYLINE':
            points = entity.get_points()
            for p in points:
                min_x, min_y = min(min_x, p[0]), min(min_y, p[1])
                max_x, max_y = max(max_x, p[0]), max(max_y, p[1])
        elif etype == 'TEXT':
            insert = entity.dxf.insert
            min_x, min_y = min(min_x, insert.x), min(min_y, insert.y)
            max_x, max_y = max(max_x, insert.x), max(max_y, insert.y)

    # Dimensions for the output preview
    width, height = 800, 600

    dx = max_x - min_x
    dy = max_y - min_y
    # Avoid division by zero if degenerate bounding box
    if dx <= 0:
        dx = 1
    if dy <= 0:
        dy = 1

    scale = min(width / dx, height / dy)

    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    offset_x = width / 2 - (min_x + max_x) / 2 * scale
    offset_y = height / 2 - (min_y + max_y) / 2 * scale

    # Draw the entities
    for entity in msp:
        etype = entity.dxftype()
        if etype == 'LINE':
            start = (
                entity.dxf.start.x * scale + offset_x,
                height - (entity.dxf.start.y * scale + offset_y)
            )
            end = (
                entity.dxf.end.x * scale + offset_x,
                height - (entity.dxf.end.y * scale + offset_y)
            )
            draw.line([start, end], fill='black', width=2)
        elif etype == 'LWPOLYLINE':
            points = [
                (p[0] * scale + offset_x, height - (p[1] * scale + offset_y))
                for p in entity.get_points()
            ]
            draw.line(points, fill='black', width=2)
        elif etype == 'TEXT':
            insert = entity.dxf.insert
            text = entity.dxf.text
            x = insert.x * scale + offset_x
            y = height - (insert.y * scale + offset_y)
            draw.text((x, y), text, fill='black')

    # Output to BytesIO as JPEG
    out_jpg = BytesIO()
    img.save(out_jpg, 'JPEG')
    out_jpg.seek(0)
    return out_jpg



def read_lines_and_polylines(dxf_bytes):

    # Print the first 500 raw bytes for debugging (optional)
    print("=== RAW DXF BYTES (first 500) ===")
    print(dxf_bytes[:500])

    # Just to confirm we have bytes
    print("Type:", type(dxf_bytes))
    print("Length:", len(dxf_bytes))

    # 1) Write the bytes to a temp file
    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp:
        tmp.write(dxf_bytes)
        tmp_path = tmp.name

    # 2) Use ezdxf.readfile(...) with the temp file
    doc = ezdxf.readfile(tmp_path)
    print("Loaded doc from temp file:", doc)






    # Print debug info
    print("DEBUG: doc object =", doc)
    print("=== All entities in doc.entities ===")
    for e in doc.entities:
        print("  -", e.dxftype)
    print(f"Total doc.entities: {len(doc.entities)}")

    # Collect shapely polylines from LWPOLYLINE entities
    polylines = [LineString([(p[0], p[1]) for p in entity.get_points()]) for entity in doc.modelspace().query('LWPOLYLINE')]

    return doc, polylines



def assign_nodes_and_get_lengths(polylines):
    """
    Takes a list of shapely LineStrings, assigns node IDs to each unique start/end,
    returns (nodes, polyline_info).
    polyline_info is a list of dicts with keys: start_node, end_node, length, start_coord, end_coord
    """
    nodes = {}
    node_id = 1
    polyline_info = []

    for line in polylines:
        coords = [tuple(map(lambda x: round(x, 4), c)) for c in line.coords]
        length = LineString(coords).length
        start, end = coords[0], coords[-1]

        for coord in [start, end]:
            if coord not in nodes:
                nodes[coord] = node_id
                node_id += 1

        polyline_info.append({
            "start_node": nodes[start],
            "end_node": nodes[end],
            "length": length,
            "start_coord": start,
            "end_coord": end
        })

    return nodes, polyline_info

def build_branches(polyline_info):
    """
    Merge any polylines that share a node (and exactly 2 polylines connect at that node).
    Return the final list of branches.
    """
    remaining = polyline_info.copy()

    while True:
        merged = False
        for polyline in remaining[:]:
            start_node = polyline['start_node']
            end_node = polyline['end_node']

            for other in remaining[:]:
                if polyline == other:
                    continue

                # Polylines that share start_node
                start_node_connections = [
                    p for p in remaining
                    if start_node in [p['start_node'], p['end_node']]
                ]
                # Polylines that share end_node
                end_node_connections = [
                    p for p in remaining
                    if end_node in [p['start_node'], p['end_node']]
                ]

                # Merge only if exactly 2 polylines connect at the node
                if len(start_node_connections) == 2 and start_node in [other['start_node'], other['end_node']]:
                    polyline['length'] += other['length']
                    # reassign start_node
                    if other['start_node'] == start_node:
                        polyline['start_node'] = other['end_node']
                    else:
                        polyline['start_node'] = other['start_node']
                    remaining.remove(other)
                    merged = True
                    break

                if len(end_node_connections) == 2 and end_node in [other['start_node'], other['end_node']]:
                    polyline['length'] += other['length']
                    # reassign end_node
                    if other['start_node'] == end_node:
                        polyline['end_node'] = other['end_node']
                    else:
                        polyline['end_node'] = other['start_node']
                    remaining.remove(other)
                    merged = True
                    break

            if merged:
                break  # restart from beginning if any merge occurred

        if not merged:
            # Stop when no merges are possible
            break

    return remaining

def save_csv(branches):
    """
    Create a CSV file from 'branches' list of dicts, returning a BytesIO object.
    """
    df = pd.DataFrame(branches, columns=[
        "start_node", "end_node", "length",
        "start_coord", "end_coord"
    ])
    out_csv = BytesIO()
    df.to_csv(out_csv, index=False)
    out_csv.seek(0)
    return out_csv

def save_dxf_with_nodes_and_polylines(doc, shapely_lines, nodes, branches):
    """
    Modify the doc (adding polylines + labeled nodes),
    then write doc to a text-based StringIO and return as BytesIO for downloading.
    """
    msp = doc.modelspace()

    # Add original lines back to doc, on layer 'ORIGINAL_POLYLINES'
    # We treat each shapely LineString as an LWPOLYLINE or a 2-point line
    for line in shapely_lines:
        coords = list(line.coords)
        msp.add_lwpolyline(coords, close=False, dxfattribs={"layer": "ORIGINAL_POLYLINES"})

    # Label node positions
    for branch in branches:
        start_coord = next(coord for coord, nid in nodes.items() if nid == branch['start_node'])
        end_coord = next(coord for coord, nid in nodes.items() if nid == branch['end_node'])

        for coord, node_id in [(start_coord, branch['start_node']), (end_coord, branch['end_node'])]:
            msp.add_text(
                str(node_id),
                dxfattribs={'height': 2, 'layer': 'FINAL_NODES'}
            ).set_dxf_attrib('insert', coord)

    # Now write doc to a text-based StringIO
    temp_stream = io.StringIO()
    doc.write(temp_stream)

    # Convert that text to bytes for a BytesIO
    dxf_bytes = temp_stream.getvalue().encode('utf-8', errors='replace')
    out_dxf = BytesIO(dxf_bytes)
    out_dxf.seek(0)
    return out_dxf

@app.route('/', endpoint='homepage')
def homepage():
    return render_template('index.html')

@app.route('/process-dxf', methods=['POST'])
def process_dxf_handler():
    global csv_io, dxf_io, jpg_io
    try:
        dxf_file = request.files.get('dxfFile')
        if not dxf_file or not dxf_file.filename.lower().endswith('.dxf'):
            return jsonify({'error': 'Invalid file type. Only DXF files are allowed.'}), 400

        # 1) Read raw bytes
        raw_bytes = dxf_file.read()

        print("Type of raw_bytes:", type(raw_bytes))
        print("Length of raw_bytes:", len(raw_bytes))

        if isinstance(raw_bytes, bytes):
            print("raw_bytes is a bytes object!")
        else:
            print("raw_bytes is NOT bytes!")

        if len(raw_bytes) == 0:
            return jsonify({'error': 'Uploaded file is empty or invalid.'}), 400

        # 3) Parse lines/polylines
        doc, shapely_lines = read_lines_and_polylines(raw_bytes)

        # 4) Node assignment
        nodes, polyline_info = assign_nodes_and_get_lengths(shapely_lines)

        # 5) Merge polylines to form branches
        branches = build_branches(polyline_info)

        # 6) Save CSV
        csv_io = save_csv(branches)

        # 7) Save updated DXF (with polylines & node labels)
        dxf_io = save_dxf_with_nodes_and_polylines(doc, shapely_lines, nodes, branches)


        # 8) Create JPG preview (uses the final doc)
        jpg_io = dxf_to_jpg(doc)

        return jsonify({
            'csv_url': '/download/final_branches.csv',
            'jpg_url': '/download/dxf_preview.jpg',
            'dxf_url': '/download/processed_output.dxf'
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    global csv_io, jpg_io, dxf_io
    if filename == 'final_branches.csv' and csv_io:
        csv_io.seek(0)
        return send_file(csv_io, as_attachment=True, download_name='final_branches.csv')

    elif filename == 'dxf_preview.jpg' and jpg_io:
        jpg_io.seek(0)
        return send_file(jpg_io, as_attachment=True, download_name='dxf_preview.jpg', mimetype='image/jpeg')

    elif filename == 'processed_output.dxf' and dxf_io:
        dxf_io.seek(0)
        return send_file(dxf_io, as_attachment=True, download_name='processed_output.dxf')

    else:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
