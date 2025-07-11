# 🏗️ SyncDub MVP - Architecture Overview

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SyncDub MVP Architecture                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Browser  │    │   Docker Host   │    │   NFS Server    │
│                 │    │                 │    │                 │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │    Web    │  │    │  │ SyncDub   │  │    │  │   Media   │  │
│  │ Interface │◄─┼────┼─►│Container  │◄─┼────┼─►│  Storage  │  │
│  │           │  │    │  │           │  │    │  │           │  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Component Architecture

### 1. **Frontend Layer**
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Components                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Upload    │  │   Media     │  │  Progress   │         │
│  │ Interface   │  │  Browser    │  │  Monitor    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ File Drag & │  │ Directory   │  │ Real-time   │         │
│  │    Drop     │  │ Navigation  │  │Notifications│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. **Backend Layer**
```
┌─────────────────────────────────────────────────────────────┐
│                     Backend Services                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    Flask    │  │     API     │  │   Media     │         │
│  │    App      │  │  Endpoints  │  │  Manager    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    Sync     │  │    File     │  │   Config    │         │
│  │  Service    │  │  Utilities  │  │  Manager    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3. **Storage Layer**
```
┌─────────────────────────────────────────────────────────────┐
│                     Storage Architecture                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Local     │  │     NFS     │  │   Output    │         │
│  │  Uploads    │  │   Volume    │  │   Storage   │         │
│  │ (Temporary) │  │ (Read-only) │  │(Processed)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    AI       │  │   Docker    │  │   Config    │         │
│  │   Models    │  │  Volumes    │  │    Files    │         │
│  │  (Cached)   │  │(Persistent) │  │ (.env, etc) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow Architecture

### 1. **File Upload Flow**
```
User Browser ──┐
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Upload Process Flow                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. File Selection                                           │
│    ┌─────────────┐    ┌─────────────┐                      │
│    │   Local     │    │     NFS     │                      │
│    │   Upload    │    │  Selection  │                      │
│    └─────────────┘    └─────────────┘                      │
│           │                    │                           │
│           └────────┬───────────┘                           │
│                    ▼                                       │
│ 2. Validation & Processing                                  │
│    ┌─────────────────────────────────┐                     │
│    │        File Validation          │                     │
│    │     ┌─────────┬─────────┐       │                     │
│    │     │ Format  │  Size   │       │                     │
│    │     │ Check   │ Check   │       │                     │
│    │     └─────────┴─────────┘       │                     │
│    └─────────────────────────────────┘                     │
│                    │                                       │
│                    ▼                                       │
│ 3. Sync Processing                                          │
│    ┌─────────────────────────────────┐                     │
│    │         AI Processing           │                     │
│    │  ┌─────────┬─────────┬───────┐  │                     │
│    │  │Whisper  │Sentence │ Sync  │  │                     │
│    │  │Transcr. │Transform│ Logic │  │                     │
│    │  └─────────┴─────────┴───────┘  │                     │
│    └─────────────────────────────────┘                     │
│                    │                                       │
│                    ▼                                       │
│ 4. Output Generation                                        │
│    ┌─────────────────────────────────┐                     │
│    │        MKV Generation           │                     │
│    │     ┌─────────┬─────────┐       │                     │
│    │     │ Video   │ Audio   │       │                     │
│    │     │ Stream  │ Tracks  │       │                     │
│    │     └─────────┴─────────┘       │                     │
│    └─────────────────────────────────┘                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. **NFS Integration Flow**
```
┌─────────────────────────────────────────────────────────────┐
│                    NFS Integration Flow                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ NFS Server ──────────────────────────────────────────────┐  │
│                                                          │  │
│ ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │  │
│ │   Movies    │    │   Series    │    │    Docs     │   │  │
│ │ Collection  │    │ Collection  │    │ Collection  │   │  │
│ └─────────────┘    └─────────────┘    └─────────────┘   │  │
│                                                          │  │
│                           │                              │  │
│                           ▼                              │  │
│ Docker Host ──────────────────────────────────────────────┘  │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                Docker Container                         │ │
│ │                                                         │ │
│ │  /app/media ◄─── NFS Mount (/mnt/nfs/media)            │ │
│ │     │                                                   │ │
│ │     ▼                                                   │ │
│ │  ┌─────────────┐    ┌─────────────┐                    │ │
│ │  │   Media     │    │ Directory   │                    │ │
│ │  │  Scanner    │    │ Navigator   │                    │ │
│ │  └─────────────┘    └─────────────┘                    │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 Security Architecture

### 1. **Permission Model**
```
┌─────────────────────────────────────────────────────────────┐
│                    Security & Permissions                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Host System (UID:GID 1000:1000)                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  NFS Mount (/mnt/nfs/media)                             │ │
│ │  ├── movies/     (1000:1000 rw)                         │ │
│ │  ├── series/     (1000:1000 rw)                         │ │
│ │  └── docs/       (1000:1000 rw)                         │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ Docker Container (User: appuser 1000:1000)                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  /app/media ◄─── Mounted Volume                         │ │
│ │  ├── movies/     (accessible)                           │ │
│ │  ├── series/     (accessible)                           │ │
│ │  └── docs/       (accessible)                           │ │
│ │                                                         │ │
│ │  /app/uploads    (1000:1000 rw)                         │ │
│ │  /app/output     (1000:1000 rw)                         │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. **Access Control**
```
┌─────────────────────────────────────────────────────────────┐
│                      Access Control                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Web Interface                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  ┌─────────────┐    ┌─────────────┐                    │ │
│ │  │   Upload    │    │   Browse    │                    │ │
│ │  │   Files     │    │    NFS      │                    │ │
│ │  │ (Write-only)│    │ (Read-only) │                    │ │
│ │  └─────────────┘    └─────────────┘                    │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ API Layer                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  ┌─────────────┐    ┌─────────────┐                    │ │
│ │  │    Path     │    │    File     │                    │ │
│ │  │ Validation  │    │ Validation  │                    │ │
│ │  └─────────────┘    └─────────────┘                    │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ File System                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  ┌─────────────┐    ┌─────────────┐                    │ │
│ │  │   Sandbox   │    │   Secure    │                    │ │
│ │  │   Access    │    │   Paths     │                    │ │
│ │  └─────────────┘    └─────────────┘                    │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Process Architecture

### 1. **Synchronization Pipeline**
```
┌─────────────────────────────────────────────────────────────┐
│                 Synchronization Pipeline                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Input Files                                                 │
│ ┌─────────────┐    ┌─────────────┐                         │
│ │  Original   │    │   Dubbed    │                         │
│ │   Video     │    │   Video     │                         │
│ └─────────────┘    └─────────────┘                         │
│        │                  │                                │
│        └─────────┬────────┘                                │
│                  ▼                                         │
│ Stage 1: Audio Extraction                                   │
│ ┌─────────────────────────────────┐                        │
│ │           FFmpeg                │                        │
│ │    ┌─────────┬─────────┐        │                        │
│ │    │Original │ Dubbed  │        │                        │
│ │    │ Audio   │ Audio   │        │                        │
│ │    └─────────┴─────────┘        │                        │
│ └─────────────────────────────────┘                        │
│                  │                                         │
│                  ▼                                         │
│ Stage 2: Transcription                                      │
│ ┌─────────────────────────────────┐                        │
│ │         OpenAI Whisper          │                        │
│ │    ┌─────────┬─────────┐        │                        │
│ │    │Original │ Dubbed  │        │                        │
│ │    │ Text +  │ Text +  │        │                        │
│ │    │Timestamps│Timestamps│       │                        │
│ │    └─────────┴─────────┘        │                        │
│ └─────────────────────────────────┘                        │
│                  │                                         │
│                  ▼                                         │
│ Stage 3: Semantic Matching                                  │
│ ┌─────────────────────────────────┐                        │
│ │      Sentence Transformers      │                        │
│ │    ┌─────────┬─────────┐        │                        │
│ │    │Semantic │Temporal │        │                        │
│ │    │Similarity│Alignment│        │                        │
│ │    └─────────┴─────────┘        │                        │
│ └─────────────────────────────────┘                        │
│                  │                                         │
│                  ▼                                         │
│ Stage 4: Synchronization                                    │
│ ┌─────────────────────────────────┐                        │
│ │        Sync Algorithm           │                        │
│ │    ┌─────────┬─────────┐        │                        │
│ │    │ Time    │ Audio   │        │                        │
│ │    │ Offset  │ Delay   │        │                        │
│ │    └─────────┴─────────┘        │                        │
│ └─────────────────────────────────┘                        │
│                  │                                         │
│                  ▼                                         │
│ Stage 5: Output Generation                                  │
│ ┌─────────────────────────────────┐                        │
│ │           MKV Muxer             │                        │
│ │    ┌─────────┬─────────┐        │                        │
│ │    │ Video   │Multiple │        │                        │
│ │    │ Stream  │ Audio   │        │                        │
│ │    │         │ Tracks  │        │                        │
│ │    └─────────┴─────────┘        │                        │
│ └─────────────────────────────────┘                        │
│                  │                                         │
│                  ▼                                         │
│ ┌─────────────────────────────────┐                        │
│ │        Synchronized             │                        │
│ │         MKV File                │                        │
│ └─────────────────────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🌐 Network Architecture

### 1. **Container Networking**
```
┌─────────────────────────────────────────────────────────────┐
│                   Network Architecture                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ External Network                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  User Browser ──────────► Port 5000 (HTTP)             │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ Docker Host                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  Docker Bridge Network (syncdub-network)               │ │
│ │  ┌─────────────────────────────────────────────────────┐│ │
│ │  │                                                     ││ │
│ │  │  SyncDub Container                                  ││ │
│ │  │  ├── Flask App (0.0.0.0:5000)                      ││ │
│ │  │  ├── API Endpoints                                  ││ │
│ │  │  └── Static Files                                   ││ │
│ │  │                                                     ││ │
│ │  └─────────────────────────────────────────────────────┘│ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ NFS Network                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  NFS Server ──────────► Port 2049 (NFS)                │ │
│ │  └── Media Storage                                      │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Performance Architecture

### 1. **Resource Management**
```
┌─────────────────────────────────────────────────────────────┐
│                  Resource Management                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ CPU Usage                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│ │  │   Whisper   │  │ Sentence    │  │   FFmpeg    │     │ │
│ │  │ Processing  │  │Transformers │  │ Processing  │     │ │
│ │  │   (High)    │  │  (Medium)   │  │   (Low)     │     │ │
│ │  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Memory Usage                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│ │  │ AI Models   │  │ Video Data  │  │ Temp Files  │     │ │
│ │  │  (4-6 GB)   │  │  (1-2 GB)   │  │  (500 MB)   │     │ │
│ │  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Storage I/O                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│ │  │ NFS Reads   │  │Local Writes │  │ Output Gen  │     │ │
│ │  │  (Medium)   │  │   (High)    │  │  (Medium)   │     │ │
│ │  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration Architecture

### 1. **Environment Configuration**
```
┌─────────────────────────────────────────────────────────────┐
│                Environment Configuration                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ .env File                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  MEDIA_SOURCE_ENABLED=true                              │ │
│ │  MEDIA_SOURCE_PATH=/mnt/nfs/media                       │ │
│ │  APP_PORT=5000                                          │ │
│ │  PUID=1000                                              │ │
│ │  PGID=1000                                              │ │
│ │  SECRET_KEY=your-secret-key                             │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ Docker Compose                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  services:                                              │ │
│ │    syncdub-app:                                         │ │
│ │      build:                                             │ │
│ │        args:                                            │ │
│ │          PUID: ${PUID:-1000}                            │ │
│ │          PGID: ${PGID:-1000}                            │ │
│ │      volumes:                                           │ │
│ │        - ${MEDIA_SOURCE_PATH}:/app/media                │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ Container Runtime                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  Environment Variables                                  │ │
│ │  ├── MEDIA_SOURCE_ENABLED                               │ │
│ │  ├── MEDIA_SOURCE_PATH                                  │ │
│ │  ├── FLASK_ENV                                          │ │
│ │  └── SECRET_KEY                                         │ │
│ │                                                         │ │
│ │  Volume Mounts                                          │ │
│ │  ├── /mnt/nfs/media → /app/media                        │ │
│ │  ├── ./uploads → /app/uploads                           │ │
│ │  └── ./output → /app/output                             │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Deployment Architecture

### 1. **Production Deployment**
```
┌─────────────────────────────────────────────────────────────┐
│                 Production Deployment                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Load Balancer (Optional)                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  HTTPS Termination                                      │ │
│ │  ├── SSL Certificates                                   │ │
│ │  ├── Rate Limiting                                      │ │
│ │  └── Health Checks                                      │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ Application Servers                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│ │  │  SyncDub    │  │  SyncDub    │  │  SyncDub    │     │ │
│ │  │Instance #1  │  │Instance #2  │  │Instance #3  │     │ │
│ │  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│ Shared Storage                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│ │  │     NFS     │  │   Shared    │  │   Backup    │     │ │
│ │  │   Media     │  │   Output    │  │  Storage    │     │ │
│ │  │   Storage   │  │   Storage   │  │             │     │ │
│ │  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

This architecture overview provides a comprehensive understanding of how SyncDub MVP is structured, from the user interface down to the storage layer, including NFS integration, security considerations, and deployment strategies.

