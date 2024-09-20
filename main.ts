import { fromEvent, merge, timer } from "rxjs";
import { filter, map, switchMap, takeUntil, tap } from "rxjs/operators";

interface KeyConfig {
  original: string;
  remapped: string;
  holdTap?: { hold: string; tap: string };
  modTap?: { mod: string; tap: string };
}

class KeyboardManager {
  private keyConfigs: KeyConfig[] = [];
  private holdTime = 200; // milliseconds

  constructor() {
    this.setupKeyboardListeners();
  }

  addKeyConfig(config: KeyConfig) {
    this.keyConfigs.push(config);
  }

  private setupKeyboardListeners() {
    const keydown$ = fromEvent<KeyboardEvent>(document, "keydown");
    const keyup$ = fromEvent<KeyboardEvent>(document, "keyup");

    merge(
      this.handleRegularKeys(keydown$),
      this.handleHoldTap(keydown$, keyup$),
      this.handleModTap(keydown$, keyup$)
    ).subscribe();
  }

  private handleRegularKeys(keydown$: any) {
    return keydown$.pipe(
      filter((event: KeyboardEvent) => !event.repeat),
      map((event: KeyboardEvent) => this.getRemappedKey(event.key)),
      filter((key: string) => key !== null),
      tap((key: string) => this.triggerKeyPress(key))
    );
  }

  private handleHoldTap(keydown$: any, keyup$: any) {
    return keydown$.pipe(
      filter((event: KeyboardEvent) => !event.repeat),
      switchMap((event: KeyboardEvent) => {
        const config = this.getKeyConfig(event.key);
        if (!config || !config.holdTap) return [];

        return timer(this.holdTime).pipe(
          takeUntil(
            keyup$.pipe(filter((e: KeyboardEvent) => e.key === event.key))
          ),
          tap(() => this.triggerKeyPress(config.holdTap!.hold)),
          takeUntil(
            keyup$.pipe(
              filter((e: KeyboardEvent) => e.key === event.key),
              tap(() => this.triggerKeyPress(config.holdTap!.tap))
            )
          )
        );
      })
    );
  }

  private handleModTap(keydown$: any, keyup$: any) {
    return keydown$.pipe(
      filter((event: KeyboardEvent) => !event.repeat),
      switchMap((event: KeyboardEvent) => {
        const config = this.getKeyConfig(event.key);
        if (!config || !config.modTap) return [];

        return timer(this.holdTime).pipe(
          takeUntil(
            keyup$.pipe(filter((e: KeyboardEvent) => e.key === event.key))
          ),
          tap(() => this.triggerKeyPress(config.modTap!.mod)),
          takeUntil(
            keyup$.pipe(
              filter((e: KeyboardEvent) => e.key === event.key),
              tap(() => {
                if (!this.isAnyKeyPressed()) {
                  this.triggerKeyPress(config.modTap!.tap);
                }
              })
            )
          )
        );
      })
    );
  }

  private getRemappedKey(key: string): string | null {
    const config = this.getKeyConfig(key);
    return config ? config.remapped : null;
  }

  private getKeyConfig(key: string): KeyConfig | undefined {
    return this.keyConfigs.find((config) => config.original === key);
  }

  private triggerKeyPress(key: string) {
    console.log(`Key pressed: ${key}`);
    // In a real implementation, you'd dispatch a new KeyboardEvent or interface with the OS
  }

  private isAnyKeyPressed(): boolean {
    // This is a simplified check. In a real implementation, you'd need to track all pressed keys
    return false;
  }
}

// Usage example
const keyboardManager = new KeyboardManager();

keyboardManager.addKeyConfig({
  original: "a",
  remapped: "b",
});

keyboardManager.addKeyConfig({
  original: "c",
  remapped: "c",
  holdTap: { hold: "ctrl", tap: "c" },
});

keyboardManager.addKeyConfig({
  original: "d",
  remapped: "d",
  modTap: { mod: "shift", tap: "d" },
});

console.log("Keyboard manager initialized. Try pressing keys!");
