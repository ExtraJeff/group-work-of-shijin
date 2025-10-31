# -*- coding: utf-8 -*-
"""
NYC应急管控研究仪表盘 - 预加载版
确保文件保存为 nyc_dashboard.py
"""

import os
import base64
import sys

# 检查并安装缺失的包
try:
    import dash
    from dash import html, dcc, Input, Output
    import dash_bootstrap_components as dbc
except ImportError as e:
    print(f"缺少依赖包: {e}")
    print("请运行: pip install dash dash-bootstrap-components")
    sys.exit(1)

# 初始化应用
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "NYC 应急管控研究仪表盘"

# 基础路径 - 请根据实际情况修改
BASE_PATH = r"C:\Users\Jeffery\Desktop\石进大作业"

# 全局缓存字典，用于存储预加载的内容
content_cache = {}

# 定义每个阶段的 HTML/图片路径
phase_htmls = {
    "Phase1": [
        ("建筑变化地图", "Phase1/outputs/maps/NYC_Building_Change_2016_2025_grid_agg.html")
    ],
    "Phase2": [
        ("行政区更新指数", "Phase2/borough_update_index_map.html")
    ],
    "Phase3": [
        ("节点时间轴", "Phase3/outputs/linknyc_nodes_timeline.html"),
        ("LinkNYC 时序地图", "Phase3/outputs/linknyc_eci_timeslider_map.html")
    ],
    "Phase4": [
        ("需求时间变化", "Phase4/outputs/building_demand_timeline_by_nta.html"),
        ("建筑需求分布", "Phase4/outputs/building_demand_map_by_nta.html")
    ],
    "Phase5": [
        ("EMCI 时间序列地图", "Phase5/outputs/emci_map_by_nta.html"),
        ("EMCI 增长率热力图", "Phase5/outputs/emci_map_by_nta_growth_heatmap.png")
    ],
    "Phase6": [
        ("EMCI 聚类空间分布", "Phase6/outputs/emci_summary_by_nta_ClusterMap.png"),
        ("PCA 聚类分析图", "Phase6/outputs/emci_summary_by_nta_PCA_clusters.png"),
        ("聚类统计对比图", "Phase6/outputs/emci_summary_by_nta_ClusterStats.png")
    ]
}

def get_phase_description(phase_num):
    """获取各阶段的简短描述"""
    descriptions = {
        1: "建筑变化分析",
        2: "更新指数计算", 
        3: "通信设施分析",
        4: "需求指数建模",
        5: "EMCI指数计算",
        6: "聚类分析"
    }
    return descriptions.get(phase_num, "分析阶段")

def preload_all_content():
    """预加载所有文件内容到内存"""
    print("🔄 预加载所有文件内容...")
    total_files = 0
    loaded_files = 0
    
    # 统计总文件数
    for phase_files in phase_htmls.values():
        total_files += len(phase_files)
    
    for phase, files in phase_htmls.items():
        for title, relative_path in files:
            full_path = os.path.join(BASE_PATH, relative_path)
            cache_key = f"{phase}_{title}"
            
            if not os.path.exists(full_path):
                content_cache[cache_key] = {
                    'type': 'missing',
                    'content': None,
                    'path': full_path
                }
                continue
            
            try:
                if full_path.endswith('.html'):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    content_cache[cache_key] = {
                        'type': 'html',
                        'content': html_content,
                        'path': full_path
                    }
                    loaded_files += 1
                    print(f"✅ 预加载 HTML: {phase} - {title}")
                    
                elif full_path.endswith('.png'):
                    with open(full_path, 'rb') as img_file:
                        encoded = base64.b64encode(img_file.read()).decode()
                        img_content = f"data:image/png;base64,{encoded}"
                    content_cache[cache_key] = {
                        'type': 'image',
                        'content': img_content,
                        'path': full_path
                    }
                    loaded_files += 1
                    print(f"✅ 预加载 图片: {phase} - {title}")
                    
            except Exception as e:
                content_cache[cache_key] = {
                    'type': 'error',
                    'content': f"加载错误: {str(e)}",
                    'path': full_path
                }
                print(f"❌ 加载失败: {phase} - {title}: {e}")
    
    print(f"📊 预加载完成: {loaded_files}/{total_files} 个文件")
    return loaded_files, total_files

def encode_image(image_path):
    """将图片转换为base64编码（备用方法）"""
    try:
        with open(image_path, 'rb') as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"图片加载失败: {image_path}, 错误: {e}")
        return None

def get_file_content(file_path):
    """读取HTML文件内容（备用方法）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"文件读取失败: {file_path}, 错误: {e}")
        return f"<h3>文件加载失败</h3><p>错误: {str(e)}</p>"

# 美化边栏
sidebar = dbc.Col(
    [
        # 顶部标题区域
        html.Div([
            html.Div(
                "🏙️",
                style={
                    'fontSize': '40px',
                    'textAlign': 'center',
                    'marginBottom': '10px'
                }
            ),
            html.H2("NYC 研究", 
                   style={
                       'textAlign': 'center', 
                       'color': '#2c3e50',
                       'fontSize': '22px',
                       'fontWeight': 'bold',
                       'marginBottom': '5px'
                   }),
            html.P("应急管控能力分析", 
                  style={
                      'textAlign': 'center', 
                      'color': '#7f8c8d',
                      'fontSize': '12px',
                      'marginBottom': '20px'
                  }),
        ], style={'padding': '20px 10px', 'borderBottom': '2px solid #e9ecef'}),
        
        # 返回主页按钮
        dbc.NavLink(
            [
                "🏠 返回主页"
            ],
            href="/",
            id="home-link",
            active="exact",
            style={
                'margin': '10px 0',
                'borderRadius': '8px',
                'fontSize': '14px',
                'fontWeight': '500',
                'padding': '12px 15px',
                'backgroundColor': '#3498db',
                'color': 'white',
                'textAlign': 'center',
                'border': 'none',
                'transition': 'all 0.3s ease'
            }
        ),
        
        html.Hr(style={'margin': '20px 0', 'borderColor': '#dee2e6'}),
        
        # 阶段导航
        html.Div([
            html.H4("📁 研究阶段", 
                   style={
                       'color': '#2c3e50',
                       'fontSize': '16px',
                       'marginBottom': '15px',
                       'paddingLeft': '10px'
                   }),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [
                            html.Span(f"Phase {i}", style={'fontWeight': 'bold'}),
                            html.Br(),
                            html.Span(get_phase_description(i), 
                                    style={'fontSize': '11px', 'color': '#95a5a6'})
                        ],
                        href=f"/phase{i}",
                        id=f"phase{i}-link",
                        active="exact",
                        style={
                            'margin': '8px 0',
                            'borderRadius': '8px',
                            'fontSize': '13px',
                            'padding': '12px 15px',
                            'border': '1px solid #e9ecef',
                            'transition': 'all 0.3s ease',
                            'color': '#495057',
                            'backgroundColor': '#f8f9fa'
                        }
                    )
                    for i in range(1, 7)
                ],
                vertical=True,
                pills=True,
            ),
        ]),
        
        # 底部信息
        html.Div([
            html.Hr(style={'margin': '25px 0 15px 0', 'borderColor': '#dee2e6'}),
            html.Div([
                html.P("🗂️ 项目信息", 
                      style={
                          'fontSize': '12px',
                          'fontWeight': 'bold',
                          'color': '#2c3e50',
                          'marginBottom': '8px'
                      }),
                html.P("NYC应急管控能力研究", 
                      style={
                          'fontSize': '11px',
                          'color': '#7f8c8d',
                          'marginBottom': '2px'
                      }),
                html.P("六阶段综合分析", 
                      style={
                          'fontSize': '11px',
                          'color': '#7f8c8d',
                          'marginBottom': '0'
                      }),
            ], style={'textAlign': 'center'})
        ], style={'marginTop': 'auto'})
    ],
    width=2,
    style={
        'backgroundColor': '#ffffff',
        'padding': '0',
        'minHeight': '100vh',
        'borderRight': '2px solid #e9ecef',
        'boxShadow': '2px 0 5px rgba(0,0,0,0.1)',
        'display': 'flex',
        'flexDirection': 'column'
    },
)

# 主内容区
content = dbc.Col(
    [
        html.Div(id="page-content", style={'padding': '20px', 'minHeight': '100vh', 'backgroundColor': '#f8f9fa'})
    ],
    width=10,
)

# 整体布局
app.layout = dbc.Container(
    [
        dcc.Location(id="url"),
        dbc.Row([sidebar, content], style={'margin': '0', 'minHeight': '100vh'}),
    ],
    fluid=True,
    style={'padding': '0', 'margin': '0', 'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#f8f9fa'}
)

# 添加自定义CSS样式到app
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .nav-link {
                color: #495057 !important;
                background-color: #f8f9fa !important;
            }
            .nav-link:hover {
                background-color: #e9ecef !important;
                color: #0056b3 !important;
                transform: translateX(5px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .nav-link.active {
                background-color: #3498db !important;
                color: white !important;
                border-color: #3498db !important;
                box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
            }
            #home-link:hover {
                background-color: #2980b9 !important;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(52, 152, 219, 0.3);
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# 主页内容
homepage_content = html.Div([
    html.Div([
        html.H1("🏙️ NYC 应急管控能力研究", 
               style={
                   'textAlign': 'center', 
                   'color': '#2c3e50', 
                   'marginBottom': '10px',
                   'fontWeight': 'bold'
               }),
        html.P("基于多源数据的城市应急管控能力综合分析平台", 
              style={
                  'textAlign': 'center', 
                  'color': '#7f8c8d', 
                  'marginBottom': '40px',
                  'fontSize': '16px'
              }),
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H4("📋 项目概述", style={'margin': '0', 'color': 'white'}),
                    style={'backgroundColor': '#3498db', 'padding': '15px'}
                ),
                dbc.CardBody([
                    html.P("本仪表盘整合了纽约市应急管控能力研究的六个阶段分析成果，涵盖从建筑变化分析到社区特征聚类的完整研究流程。", 
                          style={'lineHeight': '1.6'}),
                    html.Hr(),
                    html.H5("🔍 研究流程:", style={'color': '#2c3e50', 'marginBottom': '15px'}),
                    html.Ul([
                        html.Li([html.Strong("Phase 1: "), "建筑存量与变化时空分析"]),
                        html.Li([html.Strong("Phase 2: "), "行政区级建筑更新指数"]),
                        html.Li([html.Strong("Phase 3: "), "LinkNYC通信设施时空分布"]),
                        html.Li([html.Strong("Phase 4: "), "建筑通信需求指数建模"]),
                        html.Li([html.Strong("Phase 5: "), "应急管控能力指数(EMCI)"]),
                        html.Li([html.Strong("Phase 6: "), "社区特征聚类分析"]),
                    ], style={'lineHeight': '1.8'}),
                ], style={'padding': '25px'})
            ], className="mb-4", style={'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'})
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H4("💡 使用指南", style={'margin': '0', 'color': 'white'}),
                    style={'backgroundColor': '#27ae60', 'padding': '15px'}
                ),
                dbc.CardBody([
                    html.P("点击左侧导航栏选择不同阶段查看详细分析结果", style={'lineHeight': '1.6'}),
                    html.Hr(),
                    html.H5("📊 可视化类型:", style={'color': '#2c3e50', 'marginBottom': '15px'}),
                    html.Ul([
                        html.Li("🗺️ 交互式地图 - 支持缩放、平移"),
                        html.Li("📈 静态图表 - 聚类分析结果"),
                        html.Li("⏱️ 时间序列 - 动态变化展示"),
                    ], style={'lineHeight': '1.8'}),
                    html.Hr(),
                    html.Div([
                        html.P("🚀 性能特点:", style={'fontWeight': 'bold', 'marginBottom': '8px'}),
                        html.Ul([
                            html.Li("所有内容预加载，切换无延迟"),
                            html.Li("响应式设计，适配各种屏幕"),
                            html.Li("直观的导航体验")
                        ], style={'fontSize': '14px', 'lineHeight': '1.6'})
                    ])
                ], style={'padding': '25px'})
            ], style={'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'})
        ], width=6),
    ]),
    
    html.Div([
        html.H4("📊 系统状态", style={'marginTop': '50px', 'marginBottom': '20px', 'textAlign': 'center'}),
        html.Div(id="system-status")
    ])
], style={'maxWidth': '1200px', 'margin': '0 auto'})

# 回调函数 - 加载页面内容（使用预加载内容）
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def render_page_content(pathname):
    if pathname is None or pathname == "/":
        return homepage_content

    # 提取阶段编号
    if pathname.startswith("/phase"):
        try:
            phase_num = pathname.replace("/phase", "").strip()
            phase_key = f"Phase{phase_num}"
            
            if phase_key not in phase_htmls:
                return html.Div([
                    html.H4("❌ 阶段不存在", style={'color': '#e74c3c'}),
                    html.P(f"未找到 {phase_key} 的内容")
                ], style={'padding': '20px'})
            
            # 创建阶段内容
            elements = []
            
            # 阶段标题区域
            elements.append(
                html.Div([
                    html.H2(f"📁 {phase_key} 分析结果", 
                           style={
                               'color': '#2c3e50', 
                               'marginBottom': '10px',
                               'fontWeight': 'bold'
                           }),
                    html.P(get_phase_description(int(phase_num)), 
                          style={
                              'color': '#7f8c8d', 
                              'marginBottom': '30px',
                              'fontSize': '16px'
                          }),
                    html.Hr(style={'marginBottom': '30px'})
                ])
            )
            
            file_count = 0
            for title, relative_path in phase_htmls[phase_key]:
                cache_key = f"{phase_key}_{title}"
                
                if cache_key not in content_cache:
                    elements.append(
                        dbc.Alert([
                            html.H5(f"⚠️ 内容未预加载: {title}"),
                            html.P("请重新启动应用以预加载所有内容", style={'fontSize': '12px', 'marginBottom': '0'})
                        ], color="warning", style={'margin': '10px 0', 'borderRadius': '8px'})
                    )
                    continue
                
                cached_data = content_cache[cache_key]
                
                if cached_data['type'] == 'missing':
                    elements.append(
                        dbc.Alert([
                            html.H5(f"⚠️ 文件缺失: {title}"),
                            html.P(f"路径: {cached_data['path']}", style={'fontSize': '12px', 'marginBottom': '0'})
                        ], color="warning", style={'margin': '10px 0', 'borderRadius': '8px'})
                    )
                    continue
                
                if cached_data['type'] == 'error':
                    elements.append(
                        dbc.Alert([
                            html.H5(f"❌ 加载错误: {title}"),
                            html.P(cached_data['content'], style={'fontSize': '12px', 'marginBottom': '0'})
                        ], color="danger", style={'margin': '10px 0', 'borderRadius': '8px'})
                    )
                    continue
                
                file_count += 1
                
                # 根据文件类型显示内容
                if cached_data['type'] == 'html':
                    elements.append(html.Div([
                        html.H4(f"🗺️ {title}", 
                               style={
                                   'color': '#27ae60', 
                                   'marginBottom': '15px', 
                                   'marginTop': '30px',
                                   'fontWeight': 'bold'
                               }),
                        html.Iframe(
                            srcDoc=cached_data['content'],
                            style={
                                'width': '100%',
                                'height': '600px',
                                'border': 'none',
                                'borderRadius': '10px',
                                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
                            }
                        )
                    ]))
                    
                elif cached_data['type'] == 'image':
                    elements.append(html.Div([
                        html.H4(f"📊 {title}", 
                               style={
                                   'color': '#8e44ad', 
                                   'marginBottom': '15px', 
                                   'marginTop': '30px',
                                   'fontWeight': 'bold'
                               }),
                        html.Div(
                            html.Img(
                                src=cached_data['content'],
                                style={
                                    'maxWidth': '100%',
                                    'height': 'auto',
                                    'borderRadius': '10px',
                                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
                                    'border': '1px solid #e9ecef'
                                }
                            ),
                            style={'textAlign': 'center'}
                        )
                    ]))
            
            if file_count == 0:
                elements.append(
                    dbc.Alert([
                        html.H4("📭 暂无可用内容"),
                        html.P("该阶段的所有文件当前不可用，请检查文件路径或重新生成分析结果。")
                    ], color="info", style={
                        'textAlign': 'center', 
                        'marginTop': '50px',
                        'borderRadius': '8px'
                    })
                )
            
            return html.Div(elements, style={'maxWidth': '1200px', 'margin': '0 auto'})
            
        except Exception as e:
            return html.Div([
                dbc.Alert([
                    html.H4("❌ 加载错误"),
                    html.P(f"错误信息: {str(e)}"),
                    html.P("请检查控制台输出获取详细信息。")
                ], color="danger", style={'borderRadius': '8px'})
            ], style={'padding': '20px'})
    
    # 404页面
    return html.Div([
        dbc.Alert([
            html.H4("404 - 页面未找到"),
            html.P("请检查URL或返回主页。")
        ], color="warning", style={'borderRadius': '8px'})
    ], style={'padding': '20px'})

# 系统状态回调
@app.callback(
    Output("system-status", "children"),
    Input("url", "pathname")
)
def update_system_status(pathname):
    total_files = sum(len(files) for files in phase_htmls.values())
    loaded_files = sum(1 for data in content_cache.values() if data['type'] in ['html', 'image'])
    missing_files = sum(1 for data in content_cache.values() if data['type'] == 'missing')
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5("📊 预加载统计", style={'marginBottom': '15px', 'color': '#2c3e50'}),
                    html.Div([
                        html.Div([
                            html.Span("✅ 已加载: ", style={'fontWeight': 'bold', 'color': '#27ae60'}),
                            html.Span(f"{loaded_files}/{total_files} 个文件")
                        ], style={'marginBottom': '8px', 'fontSize': '15px'}),
                        html.Div([
                            html.Span("⚠️ 缺失文件: ", style={'fontWeight': 'bold', 'color': '#e67e22'}),
                            html.Span(f"{missing_files} 个")
                        ], style={'marginBottom': '8px', 'fontSize': '15px'}),
                        html.Div([
                            html.Span("🚀 系统状态: ", style={'fontWeight': 'bold', 'color': '#3498db'}),
                            html.Span("预加载完成，切换无延迟", style={'color': '#27ae60'})
                        ], style={'fontSize': '15px'})
                    ])
                ], width=6),
                dbc.Col([
                    html.H5("💡 性能特点", style={'marginBottom': '15px', 'color': '#2c3e50'}),
                    html.Ul([
                        html.Li("所有文件已预加载到内存"),
                        html.Li("页面切换即时响应"),
                        html.Li("支持离线查看（已加载内容）"),
                        html.Li("优化的用户体验")
                    ], style={'fontSize': '14px', 'lineHeight': '1.6'})
                ], width=6)
            ])
        ])
    ], style={'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'})

# 运行应用
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 启动NYC应急管控研究仪表盘 - 预加载版")
    print("=" * 50)
    
    # 检查基础路径
    if not os.path.exists(BASE_PATH):
        print(f"❌ 基础路径不存在: {BASE_PATH}")
        print("请修改 BASE_PATH 变量为正确的路径")
        sys.exit(1)
    
    print(f"📍 基础路径: {BASE_PATH}")
    
    # 预加载所有内容
    loaded_files, total_files = preload_all_content()
    
    print("🌐 访问地址: http://127.0.0.1:8050")
    print("💡 提示: 按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        app.run(debug=True, port=8050)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("请检查端口8050是否被占用")