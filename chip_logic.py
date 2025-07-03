# ... (所有常量和核心绘图函数与上一版本一致) ...
import json
import graphviz
import math
import re

# --- 常量定义 (与之前一致) ---
NODE_WIDTH = 180; NODE_BASE_HEIGHT = 60; PORT_RADIUS = 6; PORT_SPACING = 25;
TEXT_SIZE_MODULE_TYPE_ENHANCED = 13; MODULE_TYPE_FONT_WEIGHT = "bold"; MODULE_TYPE_TEXT_COLOR = "#1A202C";
TEXT_SIZE_LABEL = 14; TEXT_SIZE_ATTR = 11; TEXT_SIZE_PORT = 10; PADDING = 10; LINE_HEIGHT = 18;
SVG_BACKGROUND_COLOR = "white"; EDGE_STROKE_WIDTH = "3"; 
PORT_TYPE_COLORS = { 
    "DECIMAL": "#BFDBFE", "STRING": "#FEF9C3", "VECTOR": "#A7F3D0", "ENTITY": "#DDD6FE", 
    "BOOLEAN": "#FBCFE8", "ANY": "#E5E7EB", "DEFAULT": "#D1D5DB", "EXEC": "#FECACA"
}
MODULE_BASE_COLORS = { 
    "Constant (Decimal)": "#E0F2FE", "Constant (String)": "#FEFCE8", "Constant (Vector)": "#D1FAE5",
    "INPUT": "#E0E7FF", "INPUT_DECIMAL": "#E0E7FF", "INPUT_STRING": "#FEF3C7", "INPUT_VECTOR": "#D1FAE5",
    "INPUT_ENTITY": "#EDE9FE", "OUTPUT": "#E0E7FF", "OUTPUT_DECIMAL": "#E0E7FF", "OUTPUT_STRING": "#FEF3C7",
    "OUTPUT_VECTOR": "#D1FAE5", "OUTPUT_ENTITY": "#EDE9FE", "ADD": "#C7D2FE", "SUBTRACT": "#C7D2FE",
    "MULTIPLY": "#C7D2FE", "DIVIDE": "#C7D2FE", "TIME": "#A5F3FC", "Sticker": "#FFFFFF",
    "VARIABLE": "#F3E8FF", "DEFAULT": "#E5E7EB"
}
MODULE_CATALOG = { 
    "Constant (Decimal)": {"type_cn": "常量 (数值)", "display_attrs": ["value"], "fixed_width": 180, "outputs_default": [{"name": "OUTPUT", "type": "DECIMAL"}]},
    "Constant (String)": {"type_cn": "常量 (字符串)", "display_attrs": ["value"], "fixed_width": 220, "outputs_default": [{"name": "OUTPUT", "type": "STRING"}]},
    "Constant (Vector)": {"type_cn": "常量 (向量/颜色)", "display_attrs": ["value"], "fixed_width": 220, "outputs_default": [{"name": "OUTPUT", "type": "VECTOR"}]},
    "INPUT": {"type_cn_template": "输入参数 ({data_type_cn})", "display_attrs": ["name"], "fixed_width": 180, "data_type_map": {"DECIMAL": "数值", "STRING": "字符串", "VECTOR": "向量", "ENTITY": "实体", "ANY": "任意"}},
    "OUTPUT": {"type_cn_template": "输出端口 ({data_type_cn})", "display_attrs": ["name"], "fixed_width": 180, "data_type_map": {"DECIMAL": "数值", "STRING": "字符串", "VECTOR": "向量", "ENTITY": "实体", "ANY": "任意"}},
    "ADD": {"type_cn": "加法", "display_attrs": [], "inputs_default": [{"name": "A", "type": "DECIMAL"}, {"name": "B", "type": "DECIMAL"}], "outputs_default": [{"name": "A+B", "type": "DECIMAL"}]},
    "TIME": {"type_cn": "时间", "display_attrs": [], "outputs_default": [{"name": "TIME", "type": "DECIMAL"}, {"name": "DELTA TIME", "type": "DECIMAL"}, {"name": "SIN TIME", "type": "DECIMAL"}, {"name": "COS TIME", "type": "DECIMAL"}]},
    "Sticker": {"type_cn": "标签/注释", "inputs": [], "outputs": [], "display_attrs": ["Header", "Text"], "fixed_width": 250},
    "VARIABLE": {"type_cn": "变量", "display_attrs": ["name"], "variable_type_attr": "var_type"}
}

def get_module_spec(node_data_from_json):
    # ... (完整实现来自之前版本) ...
    node_type = node_data_from_json.get("type", "UnknownType"); node_attrs = node_data_from_json.get("attrs", {});
    final_spec = {"type_cn": node_type, "base_color": MODULE_BASE_COLORS.get(node_type, MODULE_BASE_COLORS["DEFAULT"]), "display_attrs": [], "inputs": [], "outputs": [], "fixed_width": NODE_WIDTH}
    catalog_entry = MODULE_CATALOG.get(node_type)
    if catalog_entry:
        final_spec["type_cn"] = catalog_entry.get("type_cn", node_type); final_spec["base_color"] = MODULE_BASE_COLORS.get(node_type, catalog_entry.get("base_color", MODULE_BASE_COLORS["DEFAULT"]));
        final_spec["display_attrs"] = list(catalog_entry.get("display_attrs", [])); final_spec["fixed_width"] = catalog_entry.get("fixed_width", NODE_WIDTH)
        if "inputs" not in node_data_from_json and "inputs_default" in catalog_entry: final_spec["inputs"] = list(catalog_entry["inputs_default"])
        if "outputs" not in node_data_from_json and "outputs_default" in catalog_entry: final_spec["outputs"] = list(catalog_entry["outputs_default"])
    if "inputs" in node_data_from_json: final_spec["inputs"] = list(node_data_from_json["inputs"])
    if "outputs" in node_data_from_json: final_spec["outputs"] = list(node_data_from_json["outputs"])
    if node_type == "INPUT":
        data_type = node_attrs.get("data_type", "ANY").upper(); data_type_cn = MODULE_CATALOG.get("INPUT", {}).get("data_type_map", {}).get(data_type, data_type)
        if final_spec["type_cn"] == node_type or not final_spec["type_cn"]: final_spec["type_cn"] = MODULE_CATALOG.get("INPUT", {}).get("type_cn_template", "输入 ({data_type_cn})").format(data_type_cn=data_type_cn)
        if not final_spec["outputs"]: final_spec["outputs"].append({"name": "OUTPUT", "type": data_type})
        if not final_spec["inputs"]: final_spec["inputs"].append({"name": "INPUT", "type": data_type})
        final_spec["base_color"] = MODULE_BASE_COLORS.get(f"INPUT_{data_type}", MODULE_BASE_COLORS.get("INPUT", MODULE_BASE_COLORS["DEFAULT"]))
    elif node_type == "OUTPUT":
        data_type = node_attrs.get("data_type", "ANY").upper(); data_type_cn = MODULE_CATALOG.get("OUTPUT", {}).get("data_type_map", {}).get(data_type, data_type)
        if final_spec["type_cn"] == node_type or not final_spec["type_cn"]: final_spec["type_cn"] = MODULE_CATALOG.get("OUTPUT", {}).get("type_cn_template", "输出 ({data_type_cn})").format(data_type_cn=data_type_cn)
        if not final_spec["inputs"]: final_spec["inputs"].append({"name": "INPUT", "type": data_type})
        final_spec["base_color"] = MODULE_BASE_COLORS.get(f"OUTPUT_{data_type}", MODULE_BASE_COLORS.get("OUTPUT", MODULE_BASE_COLORS["DEFAULT"]))
    elif node_type == "VARIABLE":
        var_type_attr_name = MODULE_CATALOG.get("VARIABLE", {}).get("variable_type_attr", "var_type"); var_type = node_attrs.get(var_type_attr_name, "ANY").upper()
        if not final_spec["inputs"]: final_spec["inputs"].extend([{"name": "INPUT", "type": var_type}, {"name": "SET", "type": "BOOLEAN"}])
        if not final_spec["outputs"]: final_spec["outputs"].append({"name": "VAR", "type": var_type})
        final_spec["base_color"] = MODULE_BASE_COLORS.get("VARIABLE", MODULE_BASE_COLORS["DEFAULT"])
    if "display_attrs" in node_data_from_json: final_spec["display_attrs"] = list(node_data_from_json["display_attrs"])
    return final_spec

def calculate_node_dimensions(node_data):
    # ... (完整实现来自之前版本) ...
    spec = get_module_spec(node_data); num_inputs = len(spec.get("inputs", [])); num_outputs = len(spec.get("outputs", [])); max_ports = max(num_inputs, num_outputs, 1)
    current_calc_height = NODE_BASE_HEIGHT
    if max_ports > 1: current_calc_height += (max_ports - 1) * PORT_SPACING
    elif max_ports == 1 and (num_inputs > 0 or num_outputs > 0): current_calc_height = max(current_calc_height, NODE_BASE_HEIGHT - PADDING + PORT_SPACING)
    attrs_to_display = spec.get("display_attrs", []); node_attrs_from_json = node_data.get("attrs", {})
    if attrs_to_display:
        num_attr_lines = 0
        for attr_key in attrs_to_display:
            if attr_key in node_attrs_from_json: num_attr_lines += len(str(node_attrs_from_json[attr_key]).split('\n'))
        if num_attr_lines > 0: current_calc_height += PADDING + num_attr_lines * (TEXT_SIZE_ATTR + 4)
    width = spec.get("fixed_width", NODE_WIDTH)
    if node_data.get("type") == "Sticker":
        header = node_attrs_from_json.get("Header", ""); text = node_attrs_from_json.get("Text", ""); max_line_len_chars = 0
        if header: max_line_len_chars = max(max_line_len_chars, len(header) * 1.2)
        if text:
            for line in text.split('\n'): max_line_len_chars = max(max_line_len_chars, len(line))
        estimated_text_width = max_line_len_chars * (TEXT_SIZE_ATTR * 0.65) + 2 * PADDING; width = max(width, int(estimated_text_width))
        sticker_height = PADDING
        if header: sticker_height += (TEXT_SIZE_LABEL + 4)
        if text: sticker_height += len(text.split('\n')) * (TEXT_SIZE_ATTR + 4)
        sticker_height += PADDING; current_calc_height = max(NODE_BASE_HEIGHT // 2, sticker_height)
    min_port_height_needed = (max_ports * PORT_SPACING) + 2 * PADDING if max_ports > 0 else 2 * PADDING
    current_calc_height = max(current_calc_height, NODE_BASE_HEIGHT, min_port_height_needed)
    return width, current_calc_height

def get_port_color(port_type):
    # ... (完整实现来自之前版本) ...
    return PORT_TYPE_COLORS.get(str(port_type).upper(), PORT_TYPE_COLORS["DEFAULT"])

def generate_node_svg(node_data, pos_x, pos_y, node_id_map):
    # ... (完整实现来自之前版本) ...
    spec = get_module_spec(node_data); node_width, node_height = node_id_map[node_data["id"]]["dimensions"]; module_type_text = spec.get("type_cn", node_data.get("type", "Unknown")); label_text = node_data.get("label", "")
    svg_parts = [f'<g transform="translate({pos_x - node_width / 2}, {pos_y - node_height / 2})">']; base_color = spec.get("base_color", MODULE_BASE_COLORS["DEFAULT"]); svg_parts.append(f'<rect x="0" y="0" width="{node_width}" height="{node_height}" rx="10" ry="10" fill="{base_color}" stroke="#4A5568" stroke-width="1.5"/>')
    current_y = PADDING + TEXT_SIZE_MODULE_TYPE_ENHANCED; svg_parts.append(f'<text x="{node_width / 2}" y="{current_y}" font-family="Arial, sans-serif" font-size="{TEXT_SIZE_MODULE_TYPE_ENHANCED}px" font-weight="{MODULE_TYPE_FONT_WEIGHT}" fill="{MODULE_TYPE_TEXT_COLOR}" text-anchor="middle">{module_type_text}</text>'); current_y += (LINE_HEIGHT * 0.9)
    if label_text: current_y += (LINE_HEIGHT * 0.9); svg_parts.append(f'<text x="{node_width / 2}" y="{current_y}" font-family="Arial, sans-serif" font-size="{TEXT_SIZE_LABEL}px" font-weight="bold" fill="#1A202C" text-anchor="middle">{label_text}</text>'); current_y += (LINE_HEIGHT * 0.7)
    node_attrs_from_json = node_data.get("attrs", {}); attrs_to_display = spec.get("display_attrs", [])
    if any(attr_key in node_attrs_from_json for attr_key in attrs_to_display):
        current_y += PADDING * 0.5
        for attr_key in attrs_to_display:
            if attr_key in node_attrs_from_json:
                attr_value = str(node_attrs_from_json[attr_key]); is_sticker = node_data.get("type") == "Sticker"; font_weight_attr = "normal"; size_attr = TEXT_SIZE_ATTR; anchor = "middle"; x_pos = node_width / 2
                if is_sticker:
                    if attr_key == "Header": font_weight_attr = "bold"; size_attr = TEXT_SIZE_LABEL; anchor = "middle"
                    elif attr_key == "Text": anchor = "start"; x_pos = PADDING
                lines = attr_value.split('\n')
                for i, line_text in enumerate(lines): svg_parts.append(f'<text x="{x_pos}" y="{current_y}" font-family="Arial, sans-serif" font-size="{size_attr}px" fill="#4A5568" text-anchor="{anchor}" font-weight="{font_weight_attr}">{line_text}</text>'); current_y += (size_attr + 4)
                current_y += 2
    inputs = spec.get("inputs", []); num_inputs = len(inputs)
    if num_inputs > 0:
        total_ports_height_inputs = (num_inputs - 1) * PORT_SPACING; start_y_inputs = (node_height / 2) - (total_ports_height_inputs / 2)
        for i, port in enumerate(inputs):
            port_name = port.get("name", f"in_{i}"); port_type = port.get("type", "ANY"); port_y = start_y_inputs + i * PORT_SPACING; port_x = 0
            node_id_map[node_data["id"]]["ports"][f"in_{port_name}"] = {"x": pos_x - node_width / 2 + port_x, "y": pos_y - node_height / 2 + port_y, "type": port_type}
            svg_parts.append(f'<circle cx="{port_x}" cy="{port_y}" r="{PORT_RADIUS}" fill="{get_port_color(port_type)}" stroke="#4A5568" stroke-width="1"/>'); svg_parts.append(f'<text x="{port_x + PORT_RADIUS + 5}" y="{port_y + TEXT_SIZE_PORT/3}" dominant-baseline="middle" font-family="Arial, sans-serif" font-size="{TEXT_SIZE_PORT}px" fill="#2D3748" text-anchor="start">{port_name}</text>')
    outputs = spec.get("outputs", []); num_outputs = len(outputs)
    if num_outputs > 0:
        total_ports_height_outputs = (num_outputs - 1) * PORT_SPACING; start_y_outputs = (node_height / 2) - (total_ports_height_outputs / 2)
        for i, port in enumerate(outputs):
            port_name = port.get("name", f"out_{i}"); port_type = port.get("type", "ANY"); port_y = start_y_outputs + i * PORT_SPACING; port_x = node_width
            node_id_map[node_data["id"]]["ports"][f"out_{port_name}"] = {"x": pos_x - node_width / 2 + port_x, "y": pos_y - node_height / 2 + port_y, "type": port_type}
            svg_parts.append(f'<circle cx="{port_x}" cy="{port_y}" r="{PORT_RADIUS}" fill="{get_port_color(port_type)}" stroke="#4A5568" stroke-width="1"/>'); svg_parts.append(f'<text x="{port_x - PORT_RADIUS - 5}" y="{port_y + TEXT_SIZE_PORT/3}" dominant-baseline="middle" font-family="Arial, sans-serif" font-size="{TEXT_SIZE_PORT}px" fill="#2D3748" text-anchor="end">{port_name}</text>')
    svg_parts.append('</g>')
    return "\n".join(svg_parts)

def generate_edge_svg(edge_data, node_id_map, spline_points_str=None):
    # ... (完整实现来自之前版本，使用固定贝塞尔曲线) ...
    from_node_id = edge_data["from_node"]; from_port_name_full = f"out_{edge_data['from_port']}"; to_node_id = edge_data["to_node"]; to_port_name_full = f"in_{edge_data['to_port']}"
    if from_node_id not in node_id_map or to_node_id not in node_id_map: return ""
    from_node_ports = node_id_map[from_node_id].get("ports", {}); to_node_ports = node_id_map[to_node_id].get("ports", {})
    if from_port_name_full not in from_node_ports or to_port_name_full not in to_node_ports: return ""
    start_port = from_node_ports[from_port_name_full]; end_port = to_node_ports[to_port_name_full]; start_x, start_y = start_port["x"], start_port["y"]; end_x, end_y = end_port["x"], end_port["y"]
    port_type = start_port.get("type", "DEFAULT"); edge_color = get_port_color(port_type)
    control_offset_x = abs(end_x - start_x) * 0.4; c1x = start_x + control_offset_x; c1y = start_y; c2x = end_x - control_offset_x; c2y = end_y      
    path_d = f"M {start_x} {start_y} C {c1x} {c1y}, {c2x} {c2y}, {end_x} {end_y}"
    return f'<path d="{path_d}" stroke="{edge_color}" stroke-width="{EDGE_STROKE_WIDTH}" fill="none" marker-end="url(#arrow-{port_type})"/>'

def generate_svg_definitions(port_types_used):
    # ... (完整实现来自之前版本) ...
    defs = "<defs>\n"
    for port_type in port_types_used:
        color = get_port_color(port_type)
        defs += f'''<marker id="arrow-{port_type}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{color}" /></marker>\n'''
    defs += "</defs>\n"
    return defs
# --- 核心逻辑函数结束 ---

def chip_json_to_svg_html(chip_data):
    """
    根据输入的芯片JSON数据，生成包含SVG图表的HTML片段。
    这个片段包含一个下载按钮和SVG图表本身。
    它不包含<html>, <head>, <body>标签，以便能被安全地内嵌到主页面。
    下载按钮的事件监听器将由主页面的JavaScript在插入此片段后添加。
    """
    # (Graphviz初始化和节点/边处理逻辑与之前版本一致)
    # ... (省略以保持简洁) ...
    dot = graphviz.Digraph(comment='Chip Diagram', graph_attr={'rankdir': 'LR', 'splines': 'spline', 'overlap': 'false','nodesep': '1.0', 'ranksep': '1.5', 'concentrate': 'false','packmode': 'node', 'sep': '+10,10'},node_attr={'shape': 'box', 'style': 'rounded,filled', 'fixedsize':'true'},edge_attr={'style': 'bold'})
    node_id_map = {}
    for node_json in chip_data.get("nodes", []): 
        node_id = node_json["id"]; width, height = calculate_node_dimensions(node_json)
        node_id_map[node_id] = {"data": node_json, "dimensions": (width, height), "ports": {}}
        gv_width_in = width / 72.0; gv_height_in = height / 72.0
        dot.node(node_id, label="", width=str(gv_width_in), height=str(gv_height_in))
    for edge_json in chip_data.get("edges", []): dot.edge(edge_json["from_node"], edge_json["to_node"])
    layout_data = None
    try:
        graph_json_str = dot.pipe(format='json').decode('utf-8'); layout_data = json.loads(graph_json_str)
    except Exception as e:
        print(f"错误：Graphviz执行失败: {e}"); print("警告：Graphviz布局失败，将使用非常基础的回退网格布局。")
        layout_data = {"objects": [], "edges": []}; node_x_start, node_y_start = 100.0, 100.0; max_width_col = 0.0; current_x, current_y = node_x_start, node_y_start; num_nodes_per_row = 3
        for i, node_id_key in enumerate(node_id_map.keys()):
            w, h = node_id_map[node_id_key]["dimensions"]
            if i > 0 and i % num_nodes_per_row == 0 : current_y += h + 70.0; current_x = node_x_start; max_width_col = 0.0
            layout_data["objects"].append({"name": node_id_key, "_gvid": i, "pos": f"{current_x + w/2},{current_y + h/2}"})
            current_x += w + 100.0; max_width_col = max(max_width_col, w)
        for idx_e, edge_entry in enumerate(chip_data.get("edges", [])):
            head_gvid = next((obj["_gvid"] for obj in layout_data["objects"] if obj["name"] == edge_entry["to_node"]), None); tail_gvid = next((obj["_gvid"] for obj in layout_data["objects"] if obj["name"] == edge_entry["from_node"]), None)
            if head_gvid is not None and tail_gvid is not None: layout_data["edges"].append({"_gvid": idx_e, "head": head_gvid, "tail": tail_gvid, "pos":""})
    all_x_coords, all_y_coords = [], []
    for gv_node in layout_data.get("objects", []):
        node_id = gv_node.get("name")
        if node_id and node_id in node_id_map:
            try:
                px, py = map(float, gv_node.get("pos", "0,0").split(','))
                node_id_map[node_id]["pos_gv"] = (px, py); w, h = node_id_map[node_id]["dimensions"]
                all_x_coords.extend([px - w / 2, px + w / 2]); all_y_coords.extend([py - h / 2, py + h / 2])
            except Exception: node_id_map[node_id]["pos_gv"] = (100.0 + len(all_x_coords) * 10, 100.0 + len(all_y_coords) * 10)
    min_gv_x = min(all_x_coords) if all_x_coords else 0.0; min_gv_y = min(all_y_coords) if all_y_coords else 0.0
    max_gv_x = max(all_x_coords) if all_x_coords else 800.0; max_gv_y = max(all_y_coords) if all_y_coords else 600.0
    svg_padding = 30.0; viewbox_width = (max_gv_x - min_gv_x) + 2 * svg_padding; viewbox_height = (max_gv_y - min_gv_y) + 2 * svg_padding
    viewbox_width = max(viewbox_width, 300.0); viewbox_height = max(viewbox_height, 200.0)
    for node_id_key in node_id_map:
        if "pos_gv" in node_id_map[node_id_key]:
            gx, gy = node_id_map[node_id_key]["pos_gv"]; svg_x = (gx - min_gv_x) + svg_padding; svg_y = (max_gv_y - gy) + svg_padding
            node_id_map[node_id_key]["pos_svg"] = (svg_x, svg_y)
        else: idx = list(node_id_map.keys()).index(node_id_key); node_id_map[node_id_key]["pos_svg"] = (svg_padding + idx * 50, svg_padding + idx * 50)
    svg_nodes_str = "";
    for node_id, data_val in node_id_map.items():
        node_item = data_val["data"]
        if "pos_svg" in data_val: pos_x, pos_y = data_val["pos_svg"]; svg_nodes_str += generate_node_svg(node_item, pos_x, pos_y, node_id_map)
    svg_edges_str = ""; port_types_in_edges = set()
    for edge in chip_data.get("edges", []):
        svg_edges_str += generate_edge_svg(edge, node_id_map, None) 
        from_port_full_name = f"out_{edge['from_port']}"
        if edge['from_node'] in node_id_map and "ports" in node_id_map[edge['from_node']] and from_port_full_name in node_id_map[edge['from_node']]["ports"]:
            port_types_in_edges.add(node_id_map[edge['from_node']]["ports"][from_port_full_name]["type"])
        else: port_types_in_edges.add("DEFAULT")
    svg_definitions = generate_svg_definitions(port_types_in_edges)
    
    # --- ⭐修改点：只返回核心的HTML片段，移除了内联的<script> ---
    # 下载按钮的ID是 "downloadGeneratedBtn"
    # SVG图表的ID是 "chipDiagramSvg_inner"
    # 主页面的JavaScript将负责为这个按钮绑定事件
    html_fragment = f"""
    <div class="diagram-controls" style="margin-bottom: 10px; text-align: center;">
        <button id="downloadGeneratedBtn" style="padding: 10px 15px; font-size: 1em; color: white; background-color: #007bff; border: none; border-radius: 5px; cursor: pointer;">下载为 JPG</button>
    </div>
    <div class="svg-render-area" style="width: 100%; height: auto; background-color: {SVG_BACKGROUND_COLOR}; border: 1px solid #ddd; overflow: auto;">
        <svg id="chipDiagramSvg_inner" viewBox="0 0 {viewbox_width} {viewbox_height}" xmlns="http://www.w3.org/2000/svg" style="display: block; max-width: 100%; height: auto;">
            {svg_definitions}
            {svg_nodes_str}
            {svg_edges_str}
        </svg>
    </div>
    """
    return html_fragment