#[tauri::command]
fn pick_folder() -> Option<String> {
    // TODO: Implement using tauri-plugin-dialog v2 if needed.
    // For now, return None to ensure the desktop app compiles and runs.
    None
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![pick_folder])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
