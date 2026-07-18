import { useState } from "react";

export function usePanelResizer(initialSidebarWidth = 250, initialEditorWidth?: number) {
  const [sidebarWidth, setSidebarWidth] = useState(initialSidebarWidth);
  const [editorWidth, setEditorWidth] = useState(() => {
    if (initialEditorWidth !== undefined) return initialEditorWidth;
    const totalWidth = typeof window !== "undefined" ? window.innerWidth : 1200;
    return Math.round((totalWidth - initialSidebarWidth) / 2);
  });

  const startResizing = (mouseDownEvent: React.MouseEvent, panel: "sidebar" | "editor") => {
    const startX = mouseDownEvent.clientX;
    const startWidth = panel === "sidebar" ? sidebarWidth : editorWidth;

    const doDrag = (mouseMoveEvent: MouseEvent) => {
      const deltaX = mouseMoveEvent.clientX - startX;
      const newWidth = startWidth + deltaX;

      const totalWidth = window.innerWidth;
      const minRightWidth = 250;
      const minSidebarWidth = 150;
      const minEditorWidth = 300;

      if (panel === "sidebar") {
        const maxSidebarWidth = totalWidth - editorWidth - minRightWidth;
        setSidebarWidth(Math.max(minSidebarWidth, Math.min(newWidth, Math.max(minSidebarWidth, maxSidebarWidth))));
      } else {
        const maxEditorWidth = totalWidth - sidebarWidth - minRightWidth;
        setEditorWidth(Math.max(minEditorWidth, Math.min(newWidth, Math.max(minEditorWidth, maxEditorWidth))));
      }
    };

    const stopDrag = () => {
      document.removeEventListener("mousemove", doDrag);
      document.removeEventListener("mouseup", stopDrag);
    };

    document.addEventListener("mousemove", doDrag);
    document.addEventListener("mouseup", stopDrag);
  };

  return {
    sidebarWidth,
    editorWidth,
    startResizing,
  };
}
