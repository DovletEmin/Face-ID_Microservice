# 🔐 Face ID — 3D Face Recognition System

> Веб-система распознавания лиц с использованием 3D-камеры Intel RealSense D415,
> аналогичная Face ID в iPhone. Микросервисная архитектура, защита от спуфинга через анализ глубины.

## Архитектура

```
                  ┌────────────────┐
                  │    Frontend    │
                  │  React + TS   │
                  │  (port 5173)  │
                  └───────┬────────┘
                          │ HTTP / WebSocket
                  ┌───────▼────────┐
                  │  API Gateway   │
                  │  FastAPI       │
                  │  (port 8000)   │
                  └──┬─────┬────┬──┘
           ┌────────┘     │     └────────┐
    ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
    │   Camera    │ │   Face    │ │    Auth     │
    │  Service    │ │ Processing│ │  Service    │
    │ (port 8001) │ │(port 8002)│ │ (port 8003) │
    │ pyrealsense │ │ InsightFace│ │   JWT      │
    └─────────────┘ └─────┬─────┘ └─────────────┘
                          │
                   ┌──────▼──────┐
                   │ PostgreSQL  │
                   │ + pgvector  │
                   │ (port 5432) │
                   └─────────────┘
```

## Технологии

| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| Camera Service | Python + pyrealsense2 | Управление камерой D415, стриминг RGB+Depth |
| Face Processing | Python + InsightFace (ArcFace) | Детекция, эмбеддинги, матчинг, анти-спуфинг |
| Auth Service | Python + FastAPI + python-jose | JWT авторизация через Face ID |
| API Gateway | Python + FastAPI | Маршрутизация, CORS, rate limiting |
| Frontend | React + TypeScript + Tailwind | Интерфейс с live-стримом камеры |
| Database | PostgreSQL + pgvector | Векторный поиск эмбеддингов лиц |
| Cache | Redis | Сессии, кэш, pub/sub |
| Containers | Docker + Docker Compose | Оркестрация микросервисов |

## Как работает

### 1. Регистрация лица (Enrollment)
1. Пользователь вводит имя и смотрит в камеру
2. Camera Service захватывает RGB + Depth кадр с RealSense D415
3. Face Processing детектирует лицо (RetinaFace)
4. Проверяется качество изображения и anti-spoofing через глубину
5. Извлекается 512-мерный эмбеддинг (ArcFace) + depth signature
6. Сохраняется в PostgreSQL с pgvector индексом

### 2. Аутентификация (Login)
1. Камера делает снимок (RGB + Depth)
2. Детекция лица → извлечение эмбеддинга
3. **Anti-spoofing проверки через depth:**
   - Наличие 3D структуры (нос выступает на 2-4см)
   - Плавность градиентов глубины
   - Допустимый диапазон глубины
   - Процент валидных depth-пикселей
4. Поиск совпадения в БД через cosine similarity (pgvector HNSW)
5. Опционально: сравнение depth signature
6. При успехе → выдаётся JWT токен

### 3. Защита от спуфинга
| Атака | Защита |
|-------|--------|
| Фото на экране | Depth = плоская поверхность → отклонено |
| Распечатанное фото | Нет 3D структуры лица → отклонено |
| Видео на экране | Плоский depth + нет nose protrusion → отклонено |
| 3D маска | Depth signature не совпадает + аномальные градиенты |

## Быстрый старт

### Требования
- Docker + Docker Compose
- Intel RealSense D415 (подключена по USB)
- 4+ GB RAM (для ML-моделей)

### Запуск

```bash
# 1. Клонируйте репозиторий
cd face_id

# 2. Скопируйте конфигурацию
cp .env.example .env
# Отредактируйте .env — измените JWT_SECRET_KEY и пароли!

# 3. Запустите все сервисы
docker-compose up -d --build

# 4. Проверьте здоровье системы
python scripts/health_check.py

# 5. Запустите фронтенд (для разработки)
cd frontend
npm install
npm run dev
```

### URL-адреса
| Сервис | URL |
|--------|-----|
| Frontend (dev) | http://localhost:5173 |
| API Gateway | http://localhost:8000 |
| API Docs (Gateway) | http://localhost:8000/docs |
| Camera Service | http://localhost:8001/docs |
| Face Service | http://localhost:8002/docs |
| Auth Service | http://localhost:8003/docs |

## API Endpoints

### Аутентификация (публичные)
```
POST /api/v1/auth/login/face         — Логин через камеру
POST /api/v1/auth/login/face/frame   — Логин с кадром от фронтенда
POST /api/v1/auth/enroll             — Регистрация через камеру
POST /api/v1/auth/enroll/frame       — Регистрация с кадром
POST /api/v1/auth/verify             — Проверка JWT токена
POST /api/v1/auth/logout             — Выход
```

### Защищённые (требуют JWT)
```
GET  /api/v1/camera/info             — Информация о камере
POST /api/v1/camera/capture          — Захват кадра
GET  /api/v1/face/users              — Список зарегистрированных
WS   /ws/camera/stream               — Live-стриминг камеры
```

### Мониторинг
```
GET  /api/v1/health                  — Статус всех сервисов
```

## Структура проекта

```
face_id/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
│
├── database/
│   ├── init.sql                     # Инициализация БД
│   └── migrations/
│       └── 001_initial.sql
│
├── services/
│   ├── camera/                      # Camera Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── schemas.py
│   │   │   ├── camera/
│   │   │   │   ├── realsense.py     # RealSense D415 драйвер
│   │   │   │   ├── depth.py         # Обработка глубины
│   │   │   │   └── stream.py        # WebSocket стриминг
│   │   │   └── api/
│   │   │       ├── routes.py
│   │   │       └── websocket.py
│   │   └── tests/
│   │
│   ├── face_processing/             # Face Processing Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── schemas.py
│   │   │   ├── camera_utils.py
│   │   │   ├── processing/
│   │   │   │   ├── detector.py      # Детекция лиц (RetinaFace)
│   │   │   │   ├── embedder.py      # Эмбеддинги (ArcFace 512-d)
│   │   │   │   ├── matcher.py       # Матчинг (pgvector cosine)
│   │   │   │   └── anti_spoof.py    # Anti-spoofing (depth)
│   │   │   ├── models/
│   │   │   │   └── face.py          # SQLAlchemy модели
│   │   │   └── api/
│   │   │       └── routes.py
│   │   └── tests/
│   │
│   ├── auth/                        # Auth Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── schemas.py
│   │   │   ├── auth/
│   │   │   │   ├── jwt_handler.py   # JWT генерация/валидация
│   │   │   │   └── face_auth.py     # Оркестрация Face ID
│   │   │   └── api/
│   │   │       └── routes.py
│   │   └── tests/
│   │
│   └── api_gateway/                 # API Gateway
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── app/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── schemas.py
│       │   ├── middleware/
│       │   │   └── auth.py          # JWT middleware
│       │   └── api/
│       │       ├── routes.py        # REST proxy
│       │       └── websocket.py     # WS proxy
│       └── tests/
│
├── frontend/                        # React Frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   ├── nginx.conf
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── CameraView.tsx       # Live камера + depth view
│       │   ├── FaceLogin.tsx        # Экран Face ID логина
│       │   ├── FaceEnroll.tsx       # Экран регистрации
│       │   └── Dashboard.tsx        # Панель после входа
│       ├── hooks/
│       │   └── useCameraStream.ts   # WebSocket hook
│       ├── services/
│       │   ├── api.ts               # REST API клиент
│       │   └── websocket.ts         # WS клиент
│       ├── store/
│       │   └── authStore.ts         # Zustand auth state
│       ├── types/
│       │   └── index.ts
│       └── styles/
│           └── globals.css
│
└── scripts/
    └── health_check.py
```

## Разработка

### Запуск отдельных сервисов (без Docker)

```bash
# Camera service
cd services/camera
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Face processing
cd services/face_processing
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Auth
cd services/auth
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# Gateway
cd services/api_gateway
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Тестирование

```bash
# Camera service tests
cd services/camera && python -m pytest tests/ -v

# Face processing tests
cd services/face_processing && python -m pytest tests/ -v

# Auth service tests
cd services/auth && python -m pytest tests/ -v
```

## Ключевые параметры

| Параметр | Значение | Описание |
|----------|----------|----------|
| `FACE_DETECTION_CONFIDENCE` | 0.7 | Минимальная уверенность детекции лица |
| `FACE_RECOGNITION_THRESHOLD` | 0.6 | Порог cosine similarity для матчинга |
| `ANTI_SPOOF_THRESHOLD` | 0.5 | Порог anti-spoofing score |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Время жизни JWT токена |
| `CAMERA_FPS` | 30 | Частота кадров стриминга |

## Лицензия

MIT
