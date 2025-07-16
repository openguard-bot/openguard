import * as React from "react"
import { Moon, Sun } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function ThemeToggle() {
  const [theme, setThemeState] = React.useState<"light" | "dark" | "system">(() => {
    if (typeof window !== "undefined") {
      const storedTheme = localStorage.getItem("vite-ui-theme");
      console.log("Initial stored theme:", storedTheme);
      if (storedTheme === "dark" || storedTheme === "light" || storedTheme === "system") {
        return storedTheme;
      }
      const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      console.log("System prefers dark:", systemPrefersDark);
      return systemPrefersDark ? "dark" : "light";
    }
    return "light";
  });

  React.useEffect(() => {
    console.log("Theme useEffect triggered. Current theme state:", theme);
    const root = window.document.documentElement;

    const shouldBeDark =
      theme === "dark" ||
      (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

    console.log("Should be dark:", shouldBeDark);

    if (shouldBeDark) {
      root.classList.add("dark");
      console.log("Added 'dark' class to root element.");
    } else {
      root.classList.remove("dark");
      console.log("Removed 'dark' class from root element.");
    }

    localStorage.setItem("vite-ui-theme", theme);
    console.log("Theme saved to localStorage:", theme);
  }, [theme]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon">
          <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => {
          setThemeState("light");
          console.log("Set theme to light.");
        }}>
          Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => {
          setThemeState("dark");
          console.log("Set theme to dark.");
        }}>
          Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => {
          setThemeState("system");
          console.log("Set theme to system.");
        }}>
          System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}