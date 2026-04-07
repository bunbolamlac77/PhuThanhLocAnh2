# Project Specification: AI Photo Culling

This document defines the high-level vision, user interface concepts, and core technical requirements for the AI Photo Culling application.

## 1. UI/UX Design Concept
The application aims for a **Futuristic/Cinematic High-End** aesthetic, optimized for clarity and visual impact on macOS.

*   **Theme**: Dark Mode Glassmorphism (Translucent backgrounds, neon glows, polished highlights).
*   **Aesthetics**: Minimalist but active. Use of gradients, smooth animations, and reactive visual feedback.
*   **Main Screen (Idle)**:
    *   Large **Dropzone Area** with a glowing dashed border.
    *   "Ripple effect" or color shift upon dragging a folder over the app.
*   **Processing Screen**:
    *   Clean layout, hiding the dropzone.
    *   **Circular Progress Bar** in the center with a smooth number counter animation (e.g., 75%).
    *   Controls: Minimalist **[Pause]** and **[Cancel]** buttons below the progress circle.
*   **Action Screen (Complete)**:
    *   Celebratory particle effect upon reaching 100%.
    *   Brief summary (e.g., "Kept 350 / 1200 photos").
    *   Two primary Call-to-Action buttons: **[COPY PHOTOS]** and **[MOVE PHOTOS]**.

## 2. Technical Stack
| Category | Technology | Notes |
| :--- | :--- | :--- |
| **Framework** | **Tauri (v2)** | Lightweight desktop bridge to Rust/System APIs. |
| **Frontend** | **ReactJS + Vite + TailwindCSS** | Modern UI development with **Framer Motion** for animations. |
| **Backend** | **Python (FastAPI)** | Local server for handling heavy AI computations. |
| **AI Runtime** | **PyTorch (MPS)** | Optimized for Apple Silicon M1 (GPU/Neural Engine). |
| **Database** | **SQLite** | Local state persistence for progress tracking and resume capability. |

## 3. File Operations & Intermediate Mapping
To ensure system stability during massive data transfers (hundreds of GBs), the AI analysis is decoupled from physical file operations.

### Step A: Intermediate `.txt` Generation
1. After AI scoring and selection, the backend generates a `selected_files.txt`.
2. This file contains the absolute paths of the winning images.
3. Automatically switches extensions from `.JPG` (processed proxy) to `.ARW` (source RAW) where applicable.

### Step B: Execution (Copy/Move)
1. User clicks **[COPY]** or **[MOVE]**.
2. Frontend triggers a minimal Python script using `shutil` or a Rust-native command.
3. The script reads the `.txt` line-by-line and performs the operation to a user-selected destination folder.
4. **Safety**: Resources (RAM/GPU) used by the AI pipeline are fully released before this stage begins.
