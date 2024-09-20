import { fromEvent, merge, timer, Observable } from "rxjs";
import { filter, map, switchMap, takeUntil, tap } from "rxjs/operators";
import * as readline from "readline";

interface KeyConfig {
  original: string;
  remapped: string;
  holdTap?: { hold: string; tap: string };
  modTap?: { mod: string; tap: string };
}

class KeyboardManager {
  private keyConfigs: KeyConfig[] = [];
  private holdTime = 200; // milliseconds
  private pressedKeys: Set<string> = new Set();

  constructor() {
    this.setupKeyboardListeners();
  }

  addKeyConfig(config: KeyConfig) {
    this.keyConfigs.push(config);
  }

  private setupKeyboardListeners() {
    readline.emitKeypressEvents(process.stdin);
    process.stdin.setRawMode(true);

    const keypress$: Observable<[string, readline.Key]> = fromEvent(
      process.stdin,
      "keypress"
    ) as Observable<[string, readline.Key]>;

    const keydown$ = keypress$.pipe(
      filter(([, key]) => !key.ctrl && !key.meta && !key.shift)
    );

    const keyup$ = keypress$.pipe(
      filter(([, key]) => key.ctrl || key.meta || key.shift)
    );

    merge(
      this.handleRegularKeys(keydown$),
      this.handleHoldTap(keydown$, keyup$),
      this.handleModTap(keydown$, keyup$)
    ).subscribe();

    // Exit on Ctrl+C
    keypress$
      .pipe(filter(([, key]) => key.ctrl && key.name === "c"))
      .subscribe(() => process.exit());
  }

  private handleRegularKeys(keydown$: Observable<[string, readline.Key]>) {
    return keydown$.pipe(
      map(([ch, key]) => this.getRemappedKey(key.name || ch)),
      filter((key: string | null) => key !== null),
      tap((key: string) => this.triggerKeyPress(key))
    );
  }

  private handleHoldTap(
    keydown$: Observable<[string, readline.Key]>,
    keyup$: Observable<[string, readline.Key]>
  ) {
    return keydown$.pipe(
      switchMap(([ch, key]) => {
        const config = this.getKeyConfig(key.name || ch);
        if (!config || !config.holdTap) return [];

        this.pressedKeys.add(key.name || ch);

        return timer(this.holdTime).pipe(
          takeUntil(keyup$.pipe(filter(([, k]) => k.name === key.name))),
          tap(() => this.triggerKeyPress(config.holdTap!.hold)),
          takeUntil(
            keyup$.pipe(
              filter(([, k]) => k.name === key.name),
              tap(() => {
                this.pressedKeys.delete(key.name || ch);
                this.triggerKeyPress(config.holdTap!.tap);
              })
            )
          )
        );
      })
    );
  }

  private handleModTap(
    keydown$: Observable<[string, readline.Key]>,
    keyup$: Observable<[string, readline.Key]>
  ) {
    return keydown$.pipe(
      switchMap(([ch, key]) => {
        const config = this.getKeyConfig(key.name || ch);
        if (!config || !config.modTap) return [];

        this.pressedKeys.add(key.name || ch);

        return timer(this.holdTime).pipe(
          takeUntil(keyup$.pipe(filter(([, k]) => k.name === key.name))),
          tap(() => this.triggerKeyPress(config.modTap!.mod)),
          takeUntil(
            keyup$.pipe(
              filter(([, k]) => k.name === key.name),
              tap(() => {
                this.pressedKeys.delete(key.name || ch);
                if (this.pressedKeys.size === 0) {
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
    return config ? config.remapped : key;
  }

  private getKeyConfig(key: string): KeyConfig | undefined {
    return this.keyConfigs.find((config) => config.original === key);
  }

  private triggerKeyPress(key: string) {
    console.log(`Key pressed: ${key}`);
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

console.log(
  "Keyboard manager initialized. Try pressing keys! (Ctrl+C to exit)"
);
