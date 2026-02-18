/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module '3dmol' {
  interface ViewerOptions {
    backgroundColor?: string
    antialias?: boolean
    cartoonQuality?: number
  }

  interface StyleSpec {
    sphere?: {
      scale?: number
      radius?: number
      color?: string
      colorscheme?: string
    }
    stick?: {
      radius?: number
      color?: string
      colorscheme?: string
      singleBonds?: boolean
    }
    cartoon?: {
      color?: string
      colorscheme?: string
    }
    line?: {
      color?: string
      colorscheme?: string
    }
  }

  interface AtomSelectionSpec {
    elem?: string
    chain?: string
    model?: number
    [key: string]: unknown
  }

  interface ModelOptions {
    doAssembly?: boolean
    duplicateAssemblyAtoms?: boolean
    [key: string]: unknown
  }

  interface GLViewer {
    addModel(data: string, format: string, options?: ModelOptions): object
    removeAllModels(): void
    removeAllSurfaces(): void
    removeAllLabels(): void
    setStyle(sel: AtomSelectionSpec, style: StyleSpec): void
    addUnitCell(): void
    zoomTo(): void
    zoom(factor: number): void
    render(): void
    resize(): void
    clear(): void
    setBackgroundColor(color: string): void
  }

  function createViewer(
    element: HTMLElement,
    options?: ViewerOptions,
  ): GLViewer
}

