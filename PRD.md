智能生活服务 APP (MVP Phase 1) 产品需求文档
文档版本	V1.0	密级	内部公开
项目名称	LifeLens (智眼生活)	技术栈	Uni-app (Vue3) + Python FastAPI
撰写人	资深产品架构师	日期	2023-10-27
核心场景	智慧餐饮（AI 视觉营养师）	开发策略	敏捷开发，Camera-First
1. 文档综述 (Executive Summary)
1.1 产品定位 (Vision)
Slogan: "LifeLens: 镜头即入口，用 AI 重构你对世界的认知。"
(LifeLens: Redef ining Perception with AI-Native Intelligence.)
1.2 MVP 策略声明
本次创新大赛版本（Phase 1）将战略性地聚焦于**“智慧餐饮”**单一垂直场景。
为何选择餐饮？
高频刚需： 饮食是最高频的生活行为，痛点（健康/热量/安全）感知最强。
技术展示度极高： 完美融合了计算机视觉（OCR/识别）、大模型推理（营养分析）和 AR 可视化，视觉冲击力强，易于在比赛演示环节抓住评委眼球。
闭环完整性： 从拍照到给出建议，业务链条短且完整，容易验证。
2. 系统架构设计 (System Architecture)
本章节是展示技术深度的核心。我们采用**“核心框架与业务插件解耦”**的设计思想，确保系统能够像搭积木一样扩展。
2.1 总体架构图 (Modular Architecture)
code
Mermaid
graph TD
    subgraph "Client Layer (Uni-app/Vue3)"
        UI[UI Presentation Layer]
        Router[App Router]
        
        subgraph "Business Modules (Plugin-based)"
            Dining[Module A: 智慧餐饮 (Active)]
            Travel[Module B: 智慧出行 (Reserved)]
            Edu[Module C: 智慧学习 (Reserved)]
        end
        
        subgraph "Core Infrastructure"
            Net[Network / Interceptor]
            Auth[User Auth / Token]
            Native[Native Bridge (Camera/Sensors)]
            Store[State Management (Pinia)]
        end
        
        UI --> Router
        Router --> Dining
        Router --> Travel
        Dining --> Net
        Dining --> Native
    end

    subgraph "Server Layer (Python FastAPI)"
        Gateway[API Gateway / Rate Limiter]
        
        subgraph "Service Layer"
            VisionSvc[Vision Service (OCR/Detection)]
            NutritionSvc[Nutrition Expert Agent]
            UserSvc[User Profile Service]
        end
        
        subgraph "AI Engine"
            LLM[Multimodal LLM API (GPT-4V/Gemini/Claude)]
            VectorDB[Vector DB (RAG Knowledge)]
        end
        
        Gateway --> VisionSvc
        VisionSvc --> LLM
        NutritionSvc --> LLM
    end

    Net <-->|HTTPS/JSON| Gateway
架构亮点说明：
模块化 (Modularity)： “餐饮”模块被设计为独立包。未来接入“出行”模块时，只需新增组件包，无需重构底层。
基础服务下沉： 网络请求、相机权限、图片压缩等通用能力被封装在 Core Infrastructure 层，实现复用。
2.2 核心数据流向图 (Data Flow: Vision Analysis)
code
Mermaid
sequenceDiagram
    participant User as 用户
    participant App as Uni-app (Frontend)
    participant API as FastAPI (Backend)
    participant LLM as 多模态大模型
    
    User->>App: 1. 唤起相机/拍摄食物
    App->>App: 2. 图片压缩 (Quality: 0.8) & 格式转换
    App->>API: 3. POST /vision/analyze (Image + UserProfile)
    activate API
    API->>API: 4. 图像预处理 (Resize/Normalize)
    API->>LLM: 5. Prompt: "Role: Nutritionist. Task: Analyze image based on profile..."
    activate LLM
    LLM-->>API: 6. 返回结构化 JSON (菜名, 热量, 建议)
    deactivate LLM
    API-->>App: 7. 返回分析结果 (AnalysisResult)
    deactivate API
    App->>App: 8. 渲染 AR 覆盖层 (Overlay UI)
    User-->>App: 9. 查看“红绿灯”建议
3. 详细功能需求 (Smart Dining Module)
3.1 P0 功能列表
ID	功能名称	优先级	描述
F-01	健康档案设置	P0	用户输入基础信息（如：减脂期、糖尿病、健身中），作为 AI 决策的 Context。
F-02	Camera-First 入口	P0	APP 启动即通过悬浮大按钮或直接进入取景模式。
F-03	视觉分析与推理	P0	处理图片上传，调用后端多模态分析接口。
F-04	AR 营养标签	P0	在原图上方通过半透明卡片展示分析结果（所见即所得）。
3.2 前端逻辑详述 (Uni-app Implementation)
A. 图像采集与压缩 (Crucial for Mobile Performance)
API 使用： 使用 uni.chooseImage，sourceType 强制设为 ['camera'] 以强化沉浸感（相册作为备选）。
Android 权限： 在 manifest.json 中声明 <uses-permission android:name="android.permission.CAMERA"/>。在调用前使用 uni.getAppAuthorizeSetting (或插件) 检查权限。
压缩策略： 为了防止 4G/弱网环境下上传超时，必须在前端进行压缩。
code
JavaScript
// 伪代码示例
uni.compressImage({
  src: tempFilePaths[0],
  quality: 60, // 压缩至 60% 质量，平衡识别率与速度
  success: res => {
    this.uploadImage(res.tempFilePath);
  }
})
B. 数据上传
实现方式： 使用 uni.uploadFile。
关键参数： formData 中必须携带用户的 profile_id 或简要健康标签（如 { "tag": "loss_weight" }），以便后端将其拼接到 Prompt 中。
C. AR 覆盖效果实现 (UI/UX)
技术难点： 图片是静态的，分析结果是动态文字。
组件方案：
底层：<image mode="widthFix"> 展示拍摄的原图。
顶层：使用 uView 的 u-transition 或标准 view 配合绝对定位 (position: absolute) 实现遮罩层。
亮点设计： 建议使用 CSS 动画实现“扫描光效”（Scanner Effect）在等待后端返回时播放，缓解用户等待焦虑。
标签渲染： 使用 cover-view (如果是 map/video 上层) 或高 z-index 的 view，绘制类似 HUD (平视显示器) 的科技感边框。
3.3 后端接口定义 (Python FastAPI)
接口：视觉膳食分析
Path: POST /api/v1/vision/analyze
Content-Type: multipart/form-data
Request:
file: Binary (Image file)
user_context: String (JSON String: {"age": 20, "goal": "muscle_gain"})
Response (JSON):
code
JSON
{
  "code": 200,
  "data": {
    "items": [
      {
        "name": "宫保鸡丁",
        "detected_box": [100, 200, 300, 400], // 预留给未来做精准位置描点
        "calories": 450,
        "unit": "kcal/100g",
        "nutrition_tags": ["高蛋白", "中碳水", "高钠"],
        "traffic_light": "yellow" // red=警告, yellow=适量, green=推荐
      }
    ],
    "total_analysis": {
      "summary": "这顿饭蛋白质充足，但酱汁含糖油较高。",
      "suggestion": "建议搭配一份水煮青菜，并少吃盘底酱汁。",
      "confidence": 0.92
    }
  },
  "trace_id": "uuid-123456" // 用于日志追踪
}
4. 未来路线图 (Roadmap)
展示架构的可扩展性，证明产品不是“一次性 Demo”。
Phase 1 (Current): 智慧餐饮 —— 解决“吃什么/健不健康”的问题。
Phase 2 (Next Quarter): 智慧出行
复用架构： 复用 Vision Service 和 LLM 接口。
场景： 拍摄路牌/景点，实时翻译并生成导游解说词。
Phase 3 (Next Year): 智慧学习
场景： 拍摄复杂题目，AI 逐步拆解解题思路（而非直接给答案）。
5. 非功能性需求 (NFR) —— 针对比赛演示优化
5.1 演示稳定性 (Demo Mode)
痛点： 比赛现场网络环境极不可控（人多拥挤、信号屏蔽）。
对策： 实现“Mock 数据兜底机制”。
在前端设置一个隐藏开关（如连续点击 Logo 5次）。
开启后，uni.uploadFile 不再请求真实服务器，而是延时 1.5秒 后直接返回本地预置的 JSON 数据（对应预置的几张演示图片）。
确保演示 100% 成功，绝不翻车。
5.2 全面屏与刘海屏适配
针对小米/OPPO 等国产机型，使用 uni.getSystemInfoSync() 获取 safeAreaInsets。
顶部 Navigation Bar 和底部的操作按钮必须避开安全区，防止被系统手势条遮挡，体现专业 UI 细节。
5.3 响应速度
设置超时时间：若后端 LLM 5秒未返回，前端先展示“AI 正在深度思考中...”的安抚动画，避免用户以为 App 卡死。