# -*- coding: utf-8 -*-

def tr(key, lang='vi'):
    data = {
        'vi': {
            'plugin_title': 'LVT have KML view - Công cụ KML chuyên nghiệp',
            'tab_shp2kml': 'Chuyển SHP → KML',
            'tab_kml2shp': 'Bung KML → SHP',
            'tab_help': 'Hướng dẫn',
            'tab_author': 'Tác giả',
            'sec_io': '1. Dữ liệu Đầu vào / Đầu ra',
            'sec_name': '2. Cấu hình Nhãn (Label trên bản đồ)',
            'sec_desc': '3. Cấu hình Popup (Thông tin chi tiết)',
            'sec_style': '4. Kiểu dáng vùng (Polygon Style)',
            'sec_style_row': '5. Tiêu đề & Tô màu dòng điều kiện',
            'lbl_layer': 'Chọn Layer từ QGIS:',
            'btn_lang': '🌐 Tiếng Việt',
            'btn_preview': '👁 Xem trước Popup',
            'btn_export': '🚀 Xuất KML/KMZ',
            'btn_save_cfg': '💾 Lưu Cấu hình',
            'btn_load_cfg': '📂 Mở Cấu hình',
            'btn_cancel': '❌ Đóng',
            'msg_success': 'Xuất file thành công!',
            'msg_config_saved': 'Đã lưu cấu hình thành công!',
            'msg_config_loaded': 'Đã tải cấu hình thành công!',
            'msg_convert_ok': 'Đã bung file sang Shapefile thành công!',
            'help_title': 'HƯỚNG DẪN SỬ DỤNG CHI TIẾT',
        },
        'en': {
            'plugin_title': 'LVT have KML view - Professional KML Tool',
            'tab_shp2kml': 'Convert SHP → KML',
            'tab_kml2shp': 'Extract KML → SHP',
            'tab_help': 'Guide',
            'tab_author': 'Author',
            'sec_io': '1. Input / Output Data',
            'sec_name': '2. Label Configuration (On-map)',
            'sec_desc': '3. Popup Configuration (Details)',
            'sec_style': '4. Polygon Styling',
            'sec_style_row': '5. Header & Conditional Row Highlight',
            'lbl_layer': 'Select QGIS Layer:',
            'btn_lang': '🌐 English',
            'btn_preview': '👁 Preview Popup',
            'btn_export': '🚀 Export KML/KMZ',
            'btn_save_cfg': '💾 Save Config',
            'btn_load_cfg': '📂 Load Config',
            'btn_cancel': '❌ Close',
            'msg_success': 'Exported successfully!',
            'msg_config_saved': 'Configuration saved!',
            'msg_config_loaded': 'Configuration loaded!',
            'msg_convert_ok': 'Extracted to Shapefile successfully!',
            'help_title': 'DETAILED USER GUIDE',
        }
    }
    return data.get(lang, data['vi']).get(key, key)

def get_help(lang='vi'):
    if lang == 'vi':
        return """
        <div style='font-size: 14px; font-family: sans-serif; line-height: 1.5;'>
        <h2 style='color:#1B5E20'>HƯỚNG DẪN SỬ DỤNG CHI TIẾT</h2>
        <p><b>1. Dữ liệu Đầu vào (SHP → KML):</b> Chọn Layer đang mở trong QGIS hoặc bấm Browse để chọn file SHP từ máy tính. Chọn định dạng KMZ để nén file gọn hơn.</p>
        <p><b>2. Cấu hình Nhãn:</b> Chọn 2 trường dữ liệu để kết hợp thành tên hiển thị trên bản đồ Google Earth. Bạn có thể xem trước kết quả ngay tại dòng chữ màu xanh.</p>
        <p><b>3. Cấu hình Popup:</b> 
            - Tick chọn các trường muốn hiển thị trong bảng thông tin.<br>
            - <b>Alias:</b> Đổi tên hiển thị cho trường (vd: 'dien_tich' thành 'Diện tích').<br>
            - <b>Hậu tố:</b> Thêm đơn vị (vd: 'ha', 'm2') sau giá trị số.
        </p>
        <p><b>4. Kiểu dáng Polygon:</b> Tùy chỉnh màu viền, độ dày và màu nền. Sử dụng thanh trượt Opacity để chỉnh độ trong suốt của vùng.</p>
        <p><b>5. Tô màu Điều kiện:</b> 
            - Nhấn <b>[+ Thêm]</b> để tạo quy tắc.<br>
            - Hệ thống hỗ trợ so sánh <b>>, <, =</b> cho các trường số và chữ.<br>
            - Dòng thỏa mãn điều kiện sẽ được đổi màu nền và màu chữ trong Popup.
        </p>
        <p><b>6. Bung KML → SHP:</b> Chọn file KML/KMZ, công cụ sẽ tự động bóc tách các trường dữ liệu từ cột Description để tạo lại file SHP có đầy đủ các cột thuộc tính riêng biệt.</p>
        </div>
        """
    else:
        return """
        <div style='font-size: 14px; font-family: sans-serif; line-height: 1.5;'>
        <h2 style='color:#1B5E20'>DETAILED USER GUIDE</h2>
        <p><b>1. Input Data (SHP → KML):</b> Select an active QGIS layer or Browse for a SHP file. Use KMZ for a more compressed output.</p>
        <p><b>2. Label Configuration:</b> Pick 2 fields to combine into the map label. See the live preview in blue text.</p>
        <p><b>3. Popup Configuration:</b> 
            - Check fields you want to show in the info table.<br>
            - <b>Alias:</b> Rename fields for display (e.g., 'area' to 'Land Area').<br>
            - <b>Suffix:</b> Add units (e.g., 'ha', 'sqm') after values.
        </p>
        <p><b>4. Polygon Styling:</b> Customize border color, width, and fill color. Use the Opacity slider to adjust transparency.</p>
        <p><b>5. Conditional Formatting:</b> 
            - Click <b>[+ Add]</b> to create a new rule.<br>
            - Supports <b>>, <, =</b> operators for numeric and text fields.<br>
            - Highlighted rows will change text and background colors in the Popup.
        </p>
        <p><b>6. Extract KML → SHP:</b> Select a KML/KMZ file. The tool will parse the Description column and reconstruct a SHP with separate attribute columns.</p>
        </div>
        """
