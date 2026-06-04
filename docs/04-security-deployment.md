# 安全部署与配置

本文档详细描述 ILsSage 智能体框架的安全部署与配置内容，对应主文档的第 7 部分。

## 7. 安全部署与配置

### 7.1 服务器配置

**.env 环境变量：**
```env
# 服务器绑定
HOST=127.0.0.1
PORT=8789

# 认证令牌（必须设置！）
GATEWAY_TOKEN=your-strong-secret-token-here

# 速率限制
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=30

# 安全配置
ALLOWED_ORIGINS=http://localhost:5173,https://your-domain.com
MAX_REQUEST_SIZE_MB=10
TOOL_EXECUTION_TIMEOUT_S=30

# 其他
DEBUG=false
LOG_LEVEL=info
```

### 7.2 多层安全防护

**1. 认证层（Auth Middleware）：**
```python
# api/middleware/auth.py
class AuthMiddleware:
    """认证中间件 - Bearer Token / Query Param 两种方式"""
    
    EXEMPT_PATHS = {"/health", "/api/health", "/chat", "/static"}
    
    async def __call__(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        token = None
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
        else:
            token = request.query_params.get("token")
        
        if not token or not self._verify_token(token):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        
        return await call_next(request)
```

**2. 速率限制（Rate Limit Middleware）：**
```python
# api/middleware/ratelimit.py
from collections import defaultdict
import time

class RateLimitMiddleware:
    """基于滑动窗口的速率限制"""
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._clients: dict[str, list] = defaultdict(list)
    
    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # 清理过期记录
        self._clients[client_ip] = [
            t for t in self._clients[client_ip] 
            if now - t < self.window
        ]
        
        if len(self._clients[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. 请稍后重试。"}
            )
        
        self._clients[client_ip].append(now)
        return await call_next(request)
```

**3. 工具权限分级：**
```python
# tools/permission.py
from enum import Enum

class ToolPermission(Enum):
    READ_ONLY = "read_only"      # 只读：文件读取、搜索
    WRITE = "write"             # 写入：文件编辑、创建
    NETWORK = "network"         # 网络：HTTP请求
    EXECUTE = "execute"         # 执行：代码运行、系统命令

class ToolPermissionManager:
    """工具权限管理器"""
    
    def __init__(self):
        self._tool_permissions: dict[str, ToolPermission] = {}
        self._session_permissions: dict[str, set[ToolPermission]] = {}
    
    def register_tool(self, tool_name: str, permission: ToolPermission):
        self._tool_permissions[tool_name] = permission
    
    def grant_session(self, session_id: str, permissions: set[ToolPermission]):
        """授予会话工具权限"""
        self._session_permissions[session_id] = permissions
    
    def can_use_tool(self, session_id: str, tool_name: str) -> bool:
        """检查会话是否有权限使用工具"""
        if session_id not in self._session_permissions:
            return False
        required = self._tool_permissions.get(tool_name, ToolPermission.READ_ONLY)
        return required in self._session_permissions[session_id]
    
    def require_confirmation(self, tool_name: str) -> bool:
        """高风险工具需要用户确认"""
        permission = self._tool_permissions.get(tool_name, ToolPermission.READ_ONLY)
        return permission in (ToolPermission.EXECUTE, ToolPermission.WRITE)
```

**4. 输入过滤：**
```python
# api/middleware/input_filter.py
import re

class InputFilter:
    """输入内容安全检查"""
    
    MAX_LENGTH = 100000  # 最大输入长度
    
    @staticmethod
    def sanitize(text: str) -> str:
        """过滤潜在危险内容"""
        if len(text) > InputFilter.MAX_LENGTH:
            raise ValueError(f"输入超过最大长度限制 ({InputFilter.MAX_LENGTH})")
        # 移除零宽字符（防止隐藏注入）
        text = re.sub(r'[\u200b-\u200f\u2028-\u202f]', '', text)
        return text
```

### 7.3 远程部署安全

1. **生产环境建议**：Nginx 反向代理 + Let's Encrypt SSL
2. **容器隔离**：Docker 部署，工具执行在独立容器中
3. **日志审计**：记录所有工具调用和模型交互
4. **定期更新**：保持依赖包和系统的安全更新
5. **最小权限原则**：运行时使用非 root 用户

### 7.4 Nginx反向代理配置

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # 速率限制
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/m;
    
    location / {
        limit_req zone=api_limit burst=10 nodelay;
        proxy_pass http://localhost:8789;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 请求大小限制
        client_max_body_size 10M;
    }
}
```

---

