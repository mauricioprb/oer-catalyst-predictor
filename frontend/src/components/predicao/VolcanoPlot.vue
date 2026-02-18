<template>
  <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-surface-600 dark:bg-surface-700">
    <PageHeader
      titulo="Dispersão - Atividade OER"
      icone="pi pi-chart-scatter"
      cor-fundo="bg-amber-100 dark:bg-amber-900/40"
      cor-icone="text-amber-600 dark:text-amber-400"
    />
    <div class="h-80">
      <Scatter :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Scatter } from 'vue-chartjs'
import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useTheme } from '@/composables/useTheme'
import type { RespostaOER } from '@/types'

ChartJS.register(LinearScale, PointElement, ChartTooltip, Legend)

const props = defineProps<{
  resultado: RespostaOER
}>()

const { temaEscuro } = useTheme()

const REFERENCIAS = [
  { label: 'RuO₂', dg_oh: 1.60, eta: 0.37 },
  { label: 'IrO₂', dg_oh: 1.50, eta: 0.56 },
  { label: 'MnO₂', dg_oh: 0.90, eta: 0.70 },
  { label: 'Co₃O₄', dg_oh: 1.25, eta: 0.48 },
  { label: 'NiOOH', dg_oh: 1.35, eta: 0.52 },
  { label: 'Fe₂O₃', dg_oh: 1.00, eta: 0.85 },
  { label: 'TiO₂', dg_oh: 0.80, eta: 1.19 },
  { label: 'PtO₂', dg_oh: 1.70, eta: 0.65 },
]

type PointStyle = 'circle' | 'rectRot'

const chartData = computed(() => {
  const refPoints = REFERENCIAS.map((r) => ({ x: r.dg_oh, y: r.eta }))

  const datasets: {
    label: string
    data: { x: number; y: number }[]
    backgroundColor: string
    borderColor: string
    borderWidth: number
    pointRadius: number
    pointHoverRadius: number
    pointStyle: PointStyle
  }[] = [
    {
      label: 'Referências (literatura)',
      data: refPoints,
      backgroundColor: temaEscuro.value ? 'rgba(148,163,184,0.5)' : '#94a3b8',
      borderColor: temaEscuro.value ? '#94a3b8' : '#64748b',
      borderWidth: 1.5,
      pointRadius: 6,
      pointHoverRadius: 8,
      pointStyle: 'circle',
    },
    {
      label: props.resultado.formula,
      data: [
        {
          x: props.resultado.adsorption_energies.delta_G_OH,
          y: props.resultado.overpotential_V,
        },
      ],
      backgroundColor: props.resultado.is_viable ? '#22c55e' : '#ef4444',
      borderColor: props.resultado.is_viable ? '#16a34a' : '#dc2626',
      borderWidth: 2,
      pointRadius: 10,
      pointHoverRadius: 12,
      pointStyle: 'rectRot',
    },
  ]

  return { datasets }
})

const chartOptions = computed(() => {
  const isDark = temaEscuro.value
  const gridColor = isDark ? 'rgba(100,116,139,0.2)' : 'rgba(148,163,184,0.15)'
  const textColor = isDark ? '#94a3b8' : '#64748b'
  const labelColor = isDark ? '#cbd5e1' : '#475569'

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
          font: { size: 11, family: 'Inter' },
          color: textColor,
        },
      },
      tooltip: {
        backgroundColor: isDark ? '#1e2128' : '#fff',
        titleColor: isDark ? '#e2e8f0' : '#1e293b',
        bodyColor: isDark ? '#cbd5e1' : '#475569',
        borderColor: isDark ? '#363b46' : '#e2e8f0',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        callbacks: {
          label: (ctx: { dataset: { label?: string }; parsed: { x: number | null; y: number | null } }) =>
            `${ctx.dataset.label}: ΔG_OH = ${(ctx.parsed.x ?? 0).toFixed(3)} eV, η = ${(ctx.parsed.y ?? 0).toFixed(3)} V`,
        },
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'ΔG_OH (eV)',
          font: { size: 12, weight: 'bold' as const, family: 'Inter' },
          color: labelColor,
        },
        grid: { color: gridColor },
        ticks: { color: textColor, font: { size: 10 } },
      },
      y: {
        title: {
          display: true,
          text: 'Overpotential η (V)',
          font: { size: 12, weight: 'bold' as const, family: 'Inter' },
          color: labelColor,
        },
        grid: { color: gridColor },
        ticks: { color: textColor, font: { size: 10 } },
        min: 0,
      },
    },
  }
})
</script>
