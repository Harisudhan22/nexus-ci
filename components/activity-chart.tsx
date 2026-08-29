'use client'

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const DATA = [
  { day: 'Aug 01', analyses: 2, uploads: 1 },
  { day: 'Aug 05', analyses: 4, uploads: 3 },
  { day: 'Aug 09', analyses: 6, uploads: 2 },
  { day: 'Aug 14', analyses: 5, uploads: 4 },
  { day: 'Aug 18', analyses: 9, uploads: 3 },
  { day: 'Aug 22', analyses: 7, uploads: 5 },
  { day: 'Aug 27', analyses: 11, uploads: 2 },
]

export function ActivityChart() {
  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={DATA} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
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
