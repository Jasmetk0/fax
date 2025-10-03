import { CSV_FILENAME, PNG_FILENAME } from "../constants";
import type { Point } from "./curve";

const triggerDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
};

/**
 * Exportuje mediánovou křivku do CSV.
 */
export function exportCurveCsv(points: Point[], filename = CSV_FILENAME) {
  const header = "age,ovr\n";
  const rows = points
    .map((point) => `${point.age.toFixed(2)},${point.ovr.toFixed(2)}`)
    .join("\n");
  const csv = `${header}${rows}`;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  triggerDownload(blob, filename);
}

const svgToCanvas = (svg: SVGSVGElement, scale = window.devicePixelRatio || 1): Promise<HTMLCanvasElement> =>
  new Promise((resolve, reject) => {
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svg);
    const encoded = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(encoded);
    const image = new Image();
    image.onload = () => {
      const rect = svg.getBoundingClientRect();
      const canvas = document.createElement("canvas");
      canvas.width = rect.width * scale;
      canvas.height = rect.height * scale;
      const context = canvas.getContext("2d");
      if (!context) {
        URL.revokeObjectURL(url);
        reject(new Error("Canvas 2D context unavailable"));
        return;
      }
      context.scale(scale, scale);
      context.drawImage(image, 0, 0, rect.width, rect.height);
      URL.revokeObjectURL(url);
      resolve(canvas);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Nelze načíst SVG pro export."));
    };
    image.src = url;
  });

/**
 * Exportuje aktuální graf do PNG.
 */
export async function exportChartPng(svg: SVGSVGElement | null, filename = PNG_FILENAME) {
  if (!svg) throw new Error("Chybí SVG element grafu.");
  const canvas = await svgToCanvas(svg);
  await new Promise<void>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("Nepodařilo se vytvořit PNG."));
        return;
      }
      triggerDownload(blob, filename);
      resolve();
    });
  });
}
