'use client'

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface ActivityPoint {
  day: string
  analyses: number
  uploads: number
}

export function ActivityChart({ data }: { data: ActivityPoint[] }) {
  const chartData = data.length > 0 ? data : [{ day: 'No data', analyses: 0, uploads: 0 }]

  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="gA" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="day"
            tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--border)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--popover)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              fontSize: 12,
              color: 'var(--popover-foreground)',
            }}
            labelStyle={{ color: 'var(--muted-foreground)' }}
          />
          <Area
            type="monotone"
            dataKey="analyses"
            name="Analyses"
            stroke="var(--primary)"
            strokeWidth={2}
            fill="url(#gA)"
          />
          <Area
            type="monotone"
            dataKey="uploads"
            name="Uploads"
            stroke="var(--chart-2)"
            strokeWidth={1.5}
            fillOpacity={0}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
