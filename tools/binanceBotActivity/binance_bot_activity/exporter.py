import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from typing import List, Dict, Any, Tuple

def generate_output_df(df_cleaned: pd.DataFrame, method: str, local_currency: str = "EUR") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Groups cleaned data by Strategy_Id and constructs the output summary dataframe
    as well as the detailed operations dataframe.
    """
    from tools.binanceBotActivity.binance_bot_activity.accounting import calculate_bot_pl_detailed
    
    output_rows = []
    all_closed_ops = []
    
    for bot_id, bot_df in df_cleaned.groupby("Strategy_Id"):
        # Sort chronologically to get correct pair and base currency metadata
        bot_df_sorted = bot_df.sort_values(by=["parsed_time", "OrderNo"], ascending=[True, True])
        
        pair = str(bot_df_sorted["Pair"].iloc[0])
        base_currency = str(bot_df_sorted["base"].iloc[0])
        
        count_buy = int((bot_df_sorted["Side"] == "BUY").sum())
        count_sell = int((bot_df_sorted["Side"] == "SELL").sum())
        
        pair_vol_buy = float(bot_df_sorted[bot_df_sorted["Side"] == "BUY"]["order_amount"].sum())
        pair_vol_sell = float(bot_df_sorted[bot_df_sorted["Side"] == "SELL"]["order_amount"].sum())
        
        base_vol_buy = float(bot_df_sorted[bot_df_sorted["Side"] == "BUY"]["total"].sum())
        base_vol_sell = float(bot_df_sorted[bot_df_sorted["Side"] == "SELL"]["total"].sum())
        
        # Calculate P&L and get detailed matched operations
        pl, pl_local, bot_closed_ops = calculate_bot_pl_detailed(bot_df_sorted, method)
        
        for op in bot_closed_ops:
            op["bot_id"] = str(bot_id)
            op["pair"] = pair
            op["base"] = base_currency
            op["local"] = local_currency
            all_closed_ops.append(op)
            
        rem_pair_amount = pair_vol_buy - pair_vol_sell
        
        output_rows.append({
            "bot_id": str(bot_id),
            "pair": pair,
            "base": base_currency,
            "local": local_currency,
            "count_buy": count_buy,
            "count_sell": count_sell,
            "pair_vol_buy": pair_vol_buy,
            "pair_vol_sell": pair_vol_sell,
            "rem_pair_amount": rem_pair_amount,
            "base_vol_buy": base_vol_buy,
            "base_vol_sell": base_vol_sell,
            "pl": pl,
            "pl_local": pl_local
        })
        
    # Sort summary by bot_id ascending
    output_rows.sort(key=lambda x: x["bot_id"])
    df_output = pd.DataFrame(output_rows)
    
    # Sort operations by Time ascending for clean chronology
    if all_closed_ops:
        df_ops = pd.DataFrame(all_closed_ops)
        df_ops = df_ops.sort_values(by=["Time", "sell_OrderNo"])
    else:
        df_ops = pd.DataFrame(columns=[
            "bot_id", "pair", "base", "local", "Time", "buy_OrderNo", "sell_OrderNo",
            "pair_amount", "base_buy_amount", "base_sell_amount", "pl_base", "pl_local",
            "buy_exchange_rate", "sell_exchange_rate"
        ])
        
    return df_output, df_ops

def generate_pair_output_df(df_cleaned: pd.DataFrame, method: str, local_currency: str = "EUR") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Groups cleaned data by Pair (regardless of Strategy_Id / bot instance) and constructs 
    the pair-level summary dataframe as well as the detailed pair-level operations dataframe.
    """
    from tools.binanceBotActivity.binance_bot_activity.accounting import calculate_bot_pl_detailed
    
    output_rows = []
    all_closed_ops = []
    
    for pair, pair_df in df_cleaned.groupby("Pair"):
        # Sort chronologically to get correct pair and base currency metadata
        pair_df_sorted = pair_df.sort_values(by=["parsed_time", "OrderNo"], ascending=[True, True])
        
        base_currency = str(pair_df_sorted["base"].iloc[0])
        
        count_buy = int((pair_df_sorted["Side"] == "BUY").sum())
        count_sell = int((pair_df_sorted["Side"] == "SELL").sum())
        
        pair_vol_buy = float(pair_df_sorted[pair_df_sorted["Side"] == "BUY"]["order_amount"].sum())
        pair_vol_sell = float(pair_df_sorted[pair_df_sorted["Side"] == "SELL"]["order_amount"].sum())
        
        base_vol_buy = float(pair_df_sorted[pair_df_sorted["Side"] == "BUY"]["total"].sum())
        base_vol_sell = float(pair_df_sorted[pair_df_sorted["Side"] == "SELL"]["total"].sum())
        
        # Calculate P&L and get detailed matched operations globally for this pair
        pl, pl_local, pair_closed_ops = calculate_bot_pl_detailed(pair_df_sorted, method)
        
        for op in pair_closed_ops:
            op["pair"] = pair
            op["base"] = base_currency
            op["local"] = local_currency
            all_closed_ops.append(op)
            
        rem_pair_amount = pair_vol_buy - pair_vol_sell
        
        output_rows.append({
            "pair": pair,
            "base": base_currency,
            "local": local_currency,
            "count_buy": count_buy,
            "count_sell": count_sell,
            "pair_vol_buy": pair_vol_buy,
            "pair_vol_sell": pair_vol_sell,
            "rem_pair_amount": rem_pair_amount,
            "base_vol_buy": base_vol_buy,
            "base_vol_sell": base_vol_sell,
            "pl": pl,
            "pl_local": pl_local
        })
        
    # Sort summary by pair ascending
    output_rows.sort(key=lambda x: x["pair"])
    df_output = pd.DataFrame(output_rows)
    
    # Sort operations by Time ascending for clean chronology
    if all_closed_ops:
        df_ops = pd.DataFrame(all_closed_ops)
        df_ops = df_ops.sort_values(by=["Time", "sell_OrderNo"])
    else:
        df_ops = pd.DataFrame(columns=[
            "pair", "base", "local", "Time", "buy_OrderNo", "sell_OrderNo",
            "pair_amount", "base_buy_amount", "base_sell_amount", "pl_base", "pl_local",
            "buy_exchange_rate", "sell_exchange_rate"
        ])
        
    return df_output, df_ops

def export_to_ods(
    df_output: pd.DataFrame, 
    df_ops: pd.DataFrame, 
    output_path: str,
    df_output_pair: pd.DataFrame = None,
    df_ops_pair: pd.DataFrame = None,
    language: str = "EN",
    country: str = "ES",
    method: str = "FIFO"
) -> None:
    """
    Exports output summaries to an OpenDocument Spreadsheet (.ods) file with four sheets:
    - Sheet 1: Explanation (comments and user guidelines in the chosen language)
    - Sheet 2: Bot Activity Summary (isolated per bot)
    - Sheet 3: Closed Operations (isolated per bot)
    - Sheet 4: Pair Activity Summary (Global FIFO, 100% Tax Compliant)
    - Sheet 5: Pair Closed Operations (Global FIFO, 100% Tax Compliant)
    Uses professional ODF styling and number formats matching the original design.
    """
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.style import Style, TextProperties, ParagraphProperties, TableCellProperties, TableColumnProperties
    from odf.table import Table, TableColumn, TableRow, TableCell
    from odf.text import P
    from odf.number import NumberStyle, Number, CurrencyStyle, CurrencySymbol

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    doc = OpenDocumentSpreadsheet()
    
    # Resolve local currency symbol
    local_currency = "EUR"
    if not df_output.empty:
        local_currency = str(df_output["local"].iloc[0])

    # 1. Register common styles
    # Number styles
    int_fmt = NumberStyle(name="int-format")
    int_fmt.addElement(Number(minintegerdigits="1", grouping="true"))
    doc.styles.addElement(int_fmt)

    crypto_fmt = NumberStyle(name="crypto-format")
    crypto_fmt.addElement(Number(decimalplaces="4", minintegerdigits="1", grouping="true"))
    doc.styles.addElement(crypto_fmt)

    currency_fmt = CurrencyStyle(name="currency-format")
    currency_fmt.addElement(CurrencySymbol(text=local_currency))
    currency_fmt.addElement(Number(decimalplaces="2", minintegerdigits="1", grouping="true"))
    doc.styles.addElement(currency_fmt)

    # Header style
    header_style = Style(name="HeaderStyle", family="table-cell")
    header_style.addElement(TableCellProperties(backgroundcolor="#1F4E79", border="0.5pt solid #D9D9D9"))
    header_style.addElement(TextProperties(attributes={"fontfamily": "Segoe UI", "fontsize": "11pt", "fontweight": "bold", "color": "#FFFFFF"}))
    header_style.addElement(ParagraphProperties(attributes={"textalign": "center"}))
    doc.automaticstyles.addElement(header_style)

    # Helper to register cell styles
    def make_cell(name, bg_color=None, text_color=None, bold=False, align="left", data_style_name=None):
        s = Style(name=name, family="table-cell", datastylename=data_style_name)
        cell_props = {"border": "0.5pt solid #D9D9D9"}
        if bg_color:
            cell_props["backgroundcolor"] = bg_color
        s.addElement(TableCellProperties(**cell_props))

        text_props = {"fontfamily": "Segoe UI", "fontsize": "10pt"}
        if text_color:
            text_props["color"] = text_color
        if bold:
            text_props["fontweight"] = "bold"
        s.addElement(TextProperties(attributes=text_props))
        s.addElement(ParagraphProperties(attributes={"textalign": align}))
        doc.automaticstyles.addElement(s)

    # Standard / Normal styles (Odd rows)
    make_cell("normal_left", align="left")
    make_cell("normal_center", align="center")
    make_cell("normal_right", align="right")
    make_cell("normal_int", align="right", data_style_name="int-format")
    make_cell("normal_crypto", align="right", data_style_name="crypto-format")
    make_cell("normal_currency", align="right", data_style_name="currency-format")
    make_cell("normal_green_bold", text_color="#375623", bold=True, align="right", data_style_name="currency-format")
    make_cell("normal_red_bold", text_color="#C00000", bold=True, align="right", data_style_name="currency-format")

    # Zebra styles (Even rows)
    zbg = "#F2F2F2"
    make_cell("zebra_left", bg_color=zbg, align="left")
    make_cell("zebra_center", bg_color=zbg, align="center")
    make_cell("zebra_right", bg_color=zbg, align="right")
    make_cell("zebra_int", bg_color=zbg, align="right", data_style_name="int-format")
    make_cell("zebra_crypto", bg_color=zbg, align="right", data_style_name="crypto-format")
    make_cell("zebra_currency", bg_color=zbg, align="right", data_style_name="currency-format")
    make_cell("zebra_green_bold", bg_color=zbg, text_color="#375623", bold=True, align="right", data_style_name="currency-format")
    make_cell("zebra_red_bold", bg_color=zbg, text_color="#C00000", bold=True, align="right", data_style_name="currency-format")

    # Value creation helper
    def build_cell(val, style_name):
        if pd.isna(val) or val == "":
            tc = TableCell(valuetype="string", stylename=style_name)
            tc.addElement(P(text=""))
            return tc
        if isinstance(val, (int, float)):
            tc = TableCell(valuetype="float", value=float(val), stylename=style_name)
            tc.addElement(P(text=str(val)))
            return tc
        tc = TableCell(valuetype="string", stylename=style_name)
        tc.addElement(P(text=str(val)))
        return tc

    # ==================== SHEET 1: Tax Explanation (Tab 0) ====================
    # Register styles specifically for Explanation tab
    title_style = Style(name="ExplTitle", family="table-cell")
    title_style.addElement(TextProperties(attributes={"fontfamily": "Segoe UI", "fontsize": "16pt", "fontweight": "bold", "color": "#1F4E79"}))
    doc.automaticstyles.addElement(title_style)

    subtitle_style = Style(name="ExplSub", family="table-cell")
    subtitle_style.addElement(TextProperties(attributes={"fontfamily": "Segoe UI", "fontsize": "11pt", "fontstyle": "italic", "color": "#595959"}))
    doc.automaticstyles.addElement(subtitle_style)

    sec_header_style = Style(name="ExplSecHeader", family="table-cell")
    sec_header_style.addElement(TableCellProperties(backgroundcolor="#1F4E79", border="0.5pt solid #D9D9D9"))
    sec_header_style.addElement(TextProperties(attributes={"fontfamily": "Segoe UI", "fontsize": "11pt", "fontweight": "bold", "color": "#FFFFFF"}))
    doc.automaticstyles.addElement(sec_header_style)

    alert_style = Style(name="ExplAlert", family="table-cell")
    alert_style.addElement(TableCellProperties(backgroundcolor="#FCE4D6", border="0.5pt solid #C00000"))
    alert_style.addElement(TextProperties(attributes={"fontfamily": "Segoe UI", "fontsize": "10pt", "fontweight": "bold", "color": "#C00000"}))
    doc.automaticstyles.addElement(alert_style)

    body_style = Style(name="ExplBody", family="table-cell")
    body_style.addElement(TextProperties(attributes={"fontfamily": "Segoe UI", "fontsize": "10pt", "color": "#000000"}))
    doc.automaticstyles.addElement(body_style)

    body_bold_style = Style(name="ExplBodyBold", family="table-cell")
    body_bold_style.addElement(TextProperties(attributes={"fontfamily": "Segoe UI", "fontsize": "10pt", "fontweight": "bold", "color": "#000000"}))
    doc.automaticstyles.addElement(body_bold_style)

    table_header_style = Style(name="ExplTabHeader", family="table-cell")
    table_header_style.addElement(TableCellProperties(backgroundcolor="#D9E1F2", border="0.5pt solid #D9D9D9"))
    table_header_style.addElement(TextProperties(attributes={"fontfamily": "Segoe UI", "fontsize": "10pt", "fontweight": "bold", "color": "#1F4E79"}))
    doc.automaticstyles.addElement(table_header_style)

    def add_text_row(table, text, style_name="ExplBody"):
        row = TableRow()
        cell = TableCell(valuetype="string", stylename=style_name)
        cell.addElement(P(text=text))
        row.addElement(cell)
        # Add empty cells to allow overflow
        for _ in range(12):
            row.addElement(TableCell())
        table.addElement(row)

    sheet_expl_name = "Explicación" if language == "ES" else "Explanation"
    table0 = Table(name=sheet_expl_name)

    if language == "ES":
        # Spanish Explanation
        add_text_row(table0, "Guía de Declaración de Impuestos para Bots de Binance", style_name="ExplTitle")
        add_text_row(table0, f"Cómo utilizar este informe para presentar su declaración de la renta en España ({country}) utilizando {method}", style_name="ExplSub")
        add_text_row(table0, "")
        
        # Alert Box
        add_text_row(table0, "¡ATENCIÓN! MUY IMPORTANTE PARA LA DECLARACIÓN DE RENTA (Hacienda):", style_name="ExplAlert")
        add_text_row(table0, "• Para su declaración en España, NO debe utilizar las pestañas de bots individuales ('Bot Activity Summary' / 'Closed Operations').", style_name="ExplAlert")
        add_text_row(table0, "• Hacienda exige aplicar el método FIFO de forma GLOBAL por activo (sin separar por bots) dentro del mismo exchange.", style_name="ExplAlert")
        add_text_row(table0, "• Por lo tanto, UTILICE los datos de la pestaña 'Pair Activity Summary' (Resumen de Actividad por Par).", style_name="ExplAlert")
        add_text_row(table0, "")

        add_text_row(table0, "Valores que debe declarar en su Modelo 100 (Casilla de Criptomonedas):", style_name="ExplBodyBold")
        add_text_row(table0, f"• Valor de adquisición (Coste total): Declare la columna 'base_vol_buy' (en {local_currency}) de la pestaña Pair Activity Summary.")
        add_text_row(table0, f"• Valor de transmisión (Venta total): Declare la columna 'base_vol_sell' (en {local_currency}) de la pestaña Pair Activity Summary.")
        add_text_row(table0, f"• Ganancia / Pérdida patrimonial neta: Declare la columna 'pl_local' (en {local_currency}) de la pestaña Pair Activity Summary.")
        add_text_row(table0, "")

        add_text_row(table0, "Descripción de las columnas del informe consolidado ('Pair Activity Summary'):", style_name="ExplBodyBold")
        
        # Mini-table header
        row = TableRow()
        for col_h in ["Columna", "Descripción", "Relevancia Fiscal"]:
            cell = TableCell(valuetype="string", stylename="ExplTabHeader")
            cell.addElement(P(text=col_h))
            row.addElement(cell)
        table0.addElement(row)

        # Mini-table rows
        col_desc_es = [
            ("pair", "El par de criptomonedas operado (ej. SOLUSDC).", "Identificación del activo."),
            ("base", "Moneda base utilizada para cotizar y comprar el activo (ej. USDC).", "Informativo."),
            ("local", "Divisa local utilizada para calcular sus impuestos (ej. EUR).", "Informativo."),
            ("count_buy / count_sell", "Número de compras y ventas realizadas.", "Informativo."),
            ("pair_vol_buy / pair_vol_sell", "Volumen total comprado/vendido en criptomonedas (ej. SOL).", "Informativo."),
            ("rem_pair_amount", "Criptomonedas restantes sin vender al final del año (saldo abierto).", "Se traslada como posición abierta al año siguiente."),
            ("base_vol_buy", "Valor total pagado en compras (en EUR) usando el tipo de cambio real del día.", "VALOR DE ADQUISICIÓN a declarar."),
            ("base_vol_sell", "Valor total recibido en ventas (en EUR) usando el tipo de cambio real del día.", "VALOR DE TRANSMISIÓN a declarar."),
            ("pl", "Ganancia / Pérdida neta calculada en la moneda base del par (ej. USDC).", "Informativo."),
            ("pl_local", "Ganancia / Pérdida neta real calculada en EUR aplicando tipos de cambio diarios.", "GANANCIA/PÉRDIDA NETA A DECLARAR.")
        ]
        for c_name, c_desc, c_tax in col_desc_es:
            row = TableRow()
            c1 = TableCell(valuetype="string", stylename="normal_left")
            c1.addElement(P(text=c_name))
            c2 = TableCell(valuetype="string", stylename="normal_left")
            c2.addElement(P(text=c_desc))
            c3 = TableCell(valuetype="string", stylename="normal_left")
            c3.addElement(P(text=c_tax))
            row.addElement(c1)
            row.addElement(c2)
            row.addElement(c3)
            table0.addElement(row)

    else:
        # English Explanation
        add_text_row(table0, "Tax Reporting Guide for Binance Trading Bots", style_name="ExplTitle")
        add_text_row(table0, f"How to use this report for your tax declaration in country ({country}) using {method}", style_name="ExplSub")
        add_text_row(table0, "")
        
        # Alert Box
        add_text_row(table0, "IMPORTANT TAX COMPLIANCE WARNING:", style_name="ExplAlert")
        add_text_row(table0, f"• For your tax declaration, DO NOT use the individual bot tabs ('Bot Activity Summary' / 'Closed Operations').", style_name="ExplAlert")
        add_text_row(table0, f"• Tax authorities generally require applying {method} globally per asset across the entire account/exchange.", style_name="ExplAlert")
        add_text_row(table0, "• Therefore, you MUST USE the consolidated data from the 'Pair Activity Summary' tab.", style_name="ExplAlert")
        add_text_row(table0, "")

        add_text_row(table0, "Values you need to report to the tax authorities:", style_name="ExplBodyBold")
        add_text_row(table0, f"• Acquisition Value (Cost basis): Report the 'base_vol_buy' column (in {local_currency}) of the Pair Activity Summary tab.")
        add_text_row(table0, f"• Sale/Transmission Value (Revenue): Report the 'base_vol_sell' column (in {local_currency}) of the Pair Activity Summary tab.")
        add_text_row(table0, f"• Net Capital Gain / Loss: Report the 'pl_local' column (in {local_currency}) of the Pair Activity Summary tab.")
        add_text_row(table0, "")

        add_text_row(table0, "Column descriptions for the unified 'Pair Activity Summary' tab:", style_name="ExplBodyBold")
        
        # Mini-table header
        row = TableRow()
        for col_h in ["Column", "Description", "Tax Relevance"]:
            cell = TableCell(valuetype="string", stylename="ExplTabHeader")
            cell.addElement(P(text=col_h))
            row.addElement(cell)
        table0.addElement(row)

        # Mini-table rows
        col_desc_en = [
            ("pair", "The cryptocurrency pair traded (e.g. SOLUSDC).", "Asset identifier."),
            ("base", "The base currency used to buy/sell the asset on Binance (e.g. USDC).", "Informational."),
            ("local", "The local currency for your tax filing (e.g. EUR).", "Informational."),
            ("count_buy / count_sell", "Total buy and sell transaction counts.", "Informational."),
            ("pair_vol_buy / pair_vol_sell", "Total traded volume in the cryptocurrency (e.g. SOL).", "Informational."),
            ("rem_pair_amount", "Unsold coins remaining at the end of the tax year.", "Carried forward as open position cost basis."),
            ("base_vol_buy", "Total amount spent on purchases (in EUR) converted at daily historical rates.", "ACQUISITION VALUE (Cost Basis) to declare."),
            ("base_vol_sell", "Total amount received from sales (in EUR) converted at daily historical rates.", "TRANSMISSION VALUE (Revenue) to declare."),
            ("pl", "Net profit calculated in the pair's base currency (e.g. USDC).", "Informational."),
            ("pl_local", "Net profit converted to EUR using real historical exchange rates.", "NET REALIZED GAIN/LOSS to declare.")
        ]
        for c_name, c_desc, c_tax in col_desc_en:
            row = TableRow()
            c1 = TableCell(valuetype="string", stylename="normal_left")
            c1.addElement(P(text=c_name))
            c2 = TableCell(valuetype="string", stylename="normal_left")
            c2.addElement(P(text=c_desc))
            c3 = TableCell(valuetype="string", stylename="normal_left")
            c3.addElement(P(text=c_tax))
            row.addElement(c1)
            row.addElement(c2)
            row.addElement(c3)
            table0.addElement(row)

    # Autostyles for Sheet 0 Columns
    c_style = Style(name="ExplCol0", family="table-column")
    c_style.addElement(TableColumnProperties(columnwidth="6.0cm"))
    doc.automaticstyles.addElement(c_style)
    table0.addElement(TableColumn(stylename="ExplCol0"))

    c_style2 = Style(name="ExplCol1", family="table-column")
    c_style2.addElement(TableColumnProperties(columnwidth="12.0cm"))
    doc.automaticstyles.addElement(c_style2)
    table0.addElement(TableColumn(stylename="ExplCol1"))

    c_style3 = Style(name="ExplCol2", family="table-column")
    c_style3.addElement(TableColumnProperties(columnwidth="7.0cm"))
    doc.automaticstyles.addElement(c_style3)
    table0.addElement(TableColumn(stylename="ExplCol2"))

    doc.spreadsheet.addElement(table0)

    # ==================== SHEET 2: Bot Activity Summary ====================
    table1 = Table(name="Bot Activity Summary")
    headers1 = [
        "bot_id", "pair", "base", "local", "count_buy", "count_sell",
        "pair_vol_buy", "pair_vol_sell", "rem_pair_amount", "base_vol_buy", "base_vol_sell", "pl", "pl_local"
    ]

    col_widths1 = {}
    
    # 1. Header row
    header_row1 = TableRow()
    for col_idx, header in enumerate(headers1):
        cell = TableCell(valuetype="string", stylename="HeaderStyle")
        cell.addElement(P(text=header))
        header_row1.addElement(cell)
        col_widths1[col_idx] = max(col_widths1.get(col_idx, 0), len(header))
    table1.addElement(header_row1)

    # 2. Data rows
    for row_idx, row_data in enumerate(df_output.to_dict(orient="records"), start=2):
        is_even = (row_idx % 2 == 0)
        prefix = "zebra_" if is_even else "normal_"
        
        vals = [
            str(row_data["bot_id"]),
            str(row_data["pair"]),
            str(row_data["base"]),
            str(row_data["local"]),
            int(row_data["count_buy"]),
            int(row_data["count_sell"]),
            float(row_data["pair_vol_buy"]),
            float(row_data["pair_vol_sell"]),
            float(row_data["rem_pair_amount"]),
            float(row_data["base_vol_buy"]),
            float(row_data["base_vol_sell"]),
            float(row_data["pl"]),
            float(row_data["pl_local"])
        ]

        row = TableRow()
        for col_idx, val in enumerate(vals):
            # Select style name
            if col_idx in [0, 1, 2, 3]:
                style_name = f"{prefix}left"
            elif col_idx in [4, 5]:
                style_name = f"{prefix}int"
            elif col_idx in [6, 7, 8, 9, 10]:
                style_name = f"{prefix}crypto"
            else: # profits
                if float(val) > 0.0001:
                    style_name = f"{prefix}green_bold"
                elif float(val) < -0.0001:
                    style_name = f"{prefix}red_bold"
                else:
                    style_name = f"{prefix}currency"

            cell = build_cell(val, style_name)
            row.addElement(cell)
            
            # Format text length for auto-fitting width
            str_val = f"{val:.4f}" if isinstance(val, float) else str(val)
            col_widths1[col_idx] = max(col_widths1.get(col_idx, 0), len(str_val))
            
        table1.addElement(row)

    # 3. Add column styles for Sheet 1
    for col_idx, max_len in col_widths1.items():
        col_style_name = f"col_style_s1_{col_idx}"
        c_style = Style(name=col_style_name, family="table-column")
        c_style.addElement(TableColumnProperties(columnwidth=f"{max(max_len * 0.22, 2.8):.2f}cm"))
        doc.automaticstyles.addElement(c_style)
        table1.addElement(TableColumn(stylename=col_style_name))

    doc.spreadsheet.addElement(table1)

    # ==================== SHEET 3: Closed Operations ====================
    table2 = Table(name="Closed Operations")
    headers2 = [
        "bot_id", "pair", "base", "local", "Time", "buy_OrderNo", "sell_OrderNo",
        "pair_amount", "base_buy_amount", "base_sell_amount", "pl_base", "pl_local",
        "buy_exchange_rate", "sell_exchange_rate"
    ]

    col_widths2 = {}

    # 1. Header row
    header_row2 = TableRow()
    for col_idx, header in enumerate(headers2):
        cell = TableCell(valuetype="string", stylename="HeaderStyle")
        cell.addElement(P(text=header))
        header_row2.addElement(cell)
        col_widths2[col_idx] = max(col_widths2.get(col_idx, 0), len(header))
    table2.addElement(header_row2)

    # 2. Data rows
    for row_idx, row_data in enumerate(df_ops.to_dict(orient="records"), start=2):
        is_even = (row_idx % 2 == 0)
        prefix = "zebra_" if is_even else "normal_"

        vals = [
            str(row_data["bot_id"]),
            str(row_data["pair"]),
            str(row_data["base"]),
            str(row_data["local"]),
            str(row_data["Time"]),
            str(row_data["buy_OrderNo"]),
            str(row_data["sell_OrderNo"]),
            float(row_data["pair_amount"]),
            float(row_data["base_buy_amount"]),
            float(row_data["base_sell_amount"]),
            float(row_data["pl_base"]),
            float(row_data["pl_local"]),
            float(row_data["buy_exchange_rate"]),
            float(row_data["sell_exchange_rate"])
        ]

        row = TableRow()
        for col_idx, val in enumerate(vals):
            if col_idx in [0, 1, 2, 3]:
                style_name = f"{prefix}left"
            elif col_idx in [4, 5, 6]:
                style_name = f"{prefix}center"
            elif col_idx in [7, 8, 9, 12, 13]:
                style_name = f"{prefix}crypto"
            else: # profits
                if float(val) > 0.0001:
                    style_name = f"{prefix}green_bold"
                elif float(val) < -0.0001:
                    style_name = f"{prefix}red_bold"
                else:
                    style_name = f"{prefix}currency"

            cell = build_cell(val, style_name)
            row.addElement(cell)

            str_val = f"{val:.4f}" if isinstance(val, float) else str(val)
            col_widths2[col_idx] = max(col_widths2.get(col_idx, 0), len(str_val))

        table2.addElement(row)

    # 3. Add column styles for Sheet 2
    for col_idx, max_len in col_widths2.items():
        col_style_name = f"col_style_s2_{col_idx}"
        c_style = Style(name=col_style_name, family="table-column")
        c_style.addElement(TableColumnProperties(columnwidth=f"{max(max_len * 0.22, 2.8):.2f}cm"))
        doc.automaticstyles.addElement(c_style)
        table2.addElement(TableColumn(stylename=col_style_name))

    doc.spreadsheet.addElement(table2)

    # ==================== SHEET 4: Pair Activity Summary ====================
    if df_output_pair is not None and not df_output_pair.empty:
        table3 = Table(name="Pair Activity Summary")
        headers3 = [
            "pair", "base", "local", "count_buy", "count_sell",
            "pair_vol_buy", "pair_vol_sell", "rem_pair_amount", "base_vol_buy", "base_vol_sell", "pl", "pl_local"
        ]

        col_widths3 = {}
        
        # 1. Header row
        header_row3 = TableRow()
        for col_idx, header in enumerate(headers3):
            cell = TableCell(valuetype="string", stylename="HeaderStyle")
            cell.addElement(P(text=header))
            header_row3.addElement(cell)
            col_widths3[col_idx] = max(col_widths3.get(col_idx, 0), len(header))
        table3.addElement(header_row3)

        # 2. Data rows
        for row_idx, row_data in enumerate(df_output_pair.to_dict(orient="records"), start=2):
            is_even = (row_idx % 2 == 0)
            prefix = "zebra_" if is_even else "normal_"
            
            vals = [
                str(row_data["pair"]),
                str(row_data["base"]),
                str(row_data["local"]),
                int(row_data["count_buy"]),
                int(row_data["count_sell"]),
                float(row_data["pair_vol_buy"]),
                float(row_data["pair_vol_sell"]),
                float(row_data["rem_pair_amount"]),
                float(row_data["base_vol_buy"]),
                float(row_data["base_vol_sell"]),
                float(row_data["pl"]),
                float(row_data["pl_local"])
            ]

            row = TableRow()
            for col_idx, val in enumerate(vals):
                if col_idx in [0, 1, 2]:
                    style_name = f"{prefix}left"
                elif col_idx in [3, 4]:
                    style_name = f"{prefix}int"
                elif col_idx in [5, 6, 7, 8, 9]:
                    style_name = f"{prefix}crypto"
                else: # profits
                    if float(val) > 0.0001:
                        style_name = f"{prefix}green_bold"
                    elif float(val) < -0.0001:
                        style_name = f"{prefix}red_bold"
                    else:
                        style_name = f"{prefix}currency"

                cell = build_cell(val, style_name)
                row.addElement(cell)
                
                str_val = f"{val:.4f}" if isinstance(val, float) else str(val)
                col_widths3[col_idx] = max(col_widths3.get(col_idx, 0), len(str_val))
                
            table3.addElement(row)

        for col_idx, max_len in col_widths3.items():
            col_style_name = f"col_style_s3_{col_idx}"
            c_style = Style(name=col_style_name, family="table-column")
            c_style.addElement(TableColumnProperties(columnwidth=f"{max(max_len * 0.22, 2.8):.2f}cm"))
            doc.automaticstyles.addElement(c_style)
            table3.addElement(TableColumn(stylename=col_style_name))

        doc.spreadsheet.addElement(table3)

    # ==================== SHEET 5: Pair Closed Operations ====================
    if df_ops_pair is not None:
        table4 = Table(name="Pair Closed Operations")
        headers4 = [
            "pair", "base", "local", "Time", "buy_OrderNo", "sell_OrderNo",
            "pair_amount", "base_buy_amount", "base_sell_amount", "pl_base", "pl_local",
            "buy_exchange_rate", "sell_exchange_rate"
        ]

        col_widths4 = {}

        # 1. Header row
        header_row4 = TableRow()
        for col_idx, header in enumerate(headers4):
            cell = TableCell(valuetype="string", stylename="HeaderStyle")
            cell.addElement(P(text=header))
            header_row4.addElement(cell)
            col_widths4[col_idx] = max(col_widths4.get(col_idx, 0), len(header))
        table4.addElement(header_row4)

        # 2. Data rows
        for row_idx, row_data in enumerate(df_ops_pair.to_dict(orient="records"), start=2):
            is_even = (row_idx % 2 == 0)
            prefix = "zebra_" if is_even else "normal_"

            vals = [
                str(row_data["pair"]),
                str(row_data["base"]),
                str(row_data["local"]),
                str(row_data["Time"]),
                str(row_data["buy_OrderNo"]),
                str(row_data["sell_OrderNo"]),
                float(row_data["pair_amount"]),
                float(row_data["base_buy_amount"]),
                float(row_data["base_sell_amount"]),
                float(row_data["pl_base"]),
                float(row_data["pl_local"]),
                float(row_data["buy_exchange_rate"]),
                float(row_data["sell_exchange_rate"])
            ]

            row = TableRow()
            for col_idx, val in enumerate(vals):
                if col_idx in [0, 1, 2]:
                    style_name = f"{prefix}left"
                elif col_idx in [3, 4, 5]:
                    style_name = f"{prefix}center"
                elif col_idx in [6, 7, 8, 11, 12]:
                    style_name = f"{prefix}crypto"
                else: # profits
                    if float(val) > 0.0001:
                        style_name = f"{prefix}green_bold"
                    elif float(val) < -0.0001:
                        style_name = f"{prefix}red_bold"
                    else:
                        style_name = f"{prefix}currency"

                cell = build_cell(val, style_name)
                row.addElement(cell)

                str_val = f"{val:.4f}" if isinstance(val, float) else str(val)
                col_widths4[col_idx] = max(col_widths4.get(col_idx, 0), len(str_val))

            table4.addElement(row)

        for col_idx, max_len in col_widths4.items():
            col_style_name = f"col_style_s4_{col_idx}"
            c_style = Style(name=col_style_name, family="table-column")
            c_style.addElement(TableColumnProperties(columnwidth=f"{max(max_len * 0.22, 2.8):.2f}cm"))
            doc.automaticstyles.addElement(c_style)
            table4.addElement(TableColumn(stylename=col_style_name))

        doc.spreadsheet.addElement(table4)

    doc.save(output_path)
