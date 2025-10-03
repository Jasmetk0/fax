import { useCallback, useEffect, useState } from "react";

export default function useLocalStorage(key: string, defaultValue: boolean) {
  const [value, setValue] = useState(defaultValue);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(key);
      if (stored === "true" || stored === "false") {
        setValue(stored === "true");
      }
    } catch (error) {
      console.warn("Failed to read localStorage", error);
    }
  }, [key]);

  const update = useCallback(
    (next: boolean | ((current: boolean) => boolean)) => {
      setValue((current) => {
        const resolved = typeof next === "function" ? (next as (current: boolean) => boolean)(current) : next;
        try {
          window.localStorage.setItem(key, resolved ? "true" : "false");
        } catch (error) {
          console.warn("Failed to write localStorage", error);
        }
        return resolved;
      });
    },
    [key]
  );

  return [value, update] as const;
}
