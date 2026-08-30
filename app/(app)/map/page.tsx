"use client"

import { useState, useEffect } from "react"
import { PageHeader } from "@/components/page-header"
import { MapPin, Navigation, Layers, Shield, Building2, Users, Car } from "lucide-react"

interface GeocodedPoint {
  id: string
  name: string
  category: string
  lat: number
  lng: number
  caseIds: string[]
  details: string
}

const DEMO_POINTS: GeocodedPoint[] = [
  { id: "loc-1", name: "Central Station PS", category: "Police Station", lat: 13.0827, lng: 80.2707, caseIds: ["case-101", "case-501"], details: "Intercepted white sedan TN01AB1234 driven by R. Kumar." },
  { id: "loc-2", name: "State Bank of India Main Branch", category: "Financial Institution", lat: 13.0839, lng: 80.2826, caseIds: ["case-205"], details: "Account A101 cash deposits and wire routing origin." },
  { id: "loc-3", name: "Airport Surveillance Sector", category: "Surveillance", lat: 12.9941, lng: 80.1709, caseIds: ["case-301"], details: "CCTV detection of target phone 9876543210." },
  { id: "loc-4", name: "State Crime Branch HQ", category: "HQ", lat: 13.0604, lng: 80.2496, caseIds: ["case-101", "case-203", "case-205", "case-301", "case-412"], details: "Central case coordination command." }
]

export default function GeospatialMapPage() {
  const [selectedPoint, setSelectedPoint] = useState<GeocodedPoint>(DEMO_POINTS[0])
  const [activeCategory, setActiveCategory] = useState<string>("all")

  const filteredPoints = DEMO_POINTS.filter((p) => activeCategory === "all" || p.category.toLowerCase().includes(activeCategory.toLowerCase()))

  return (
    <div>
      <PageHeader
        eyebrow="Geospatial Intelligence"
        title="Operational Map & Movement Timeline"
        description="Geographic clustering and spatial movement tracking anchored strictly to verified evidence coordinates."
      />

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Map Canvas (8 Cols) */}
          <div className="lg:col-span-8 rounded-lg border border-border bg-card shadow-sm overflow-hidden flex flex-col h-[520px]">
            <div className="p-3 border-b border-border bg-muted/20 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MapPin className="size-4 text-primary" />
                <span className="text-xs font-semibold text-foreground">Spatial Cluster Canvas (Chennai Sector)</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveCategory("all")}
                  className={`px-2.5 py-1 rounded text-xs font-medium ${activeCategory === "all" ? "bg-primary text-primary-foreground" : "bg-background border border-border"}`}
                >
                  All Locations ({DEMO_POINTS.length})
                </button>
              </div>
            </div>

            {/* Embedded OpenStreetMap Tile IFrame Canvas */}
            <div className="flex-1 relative bg-muted/30">
              <iframe
                title="Geospatial Map"
                width="100%"
                height="100%"
                frameBorder="0"
                scrolling="no"
                src={`https://www.openstreetmap.org/export/embed.html?bbox=80.1000%2C12.9500%2C80.3500%2C13.1500&layer=mapnik&marker=${selectedPoint.lat}%2C${selectedPoint.lng}`}
                className="w-full h-full border-0 filter grayscale contrast-125 opacity-90"
              />

              {/* Floating Overlay Pins */}
              <div className="absolute top-4 right-4 bg-card/90 backdrop-blur border border-border p-3 rounded-lg shadow-md space-y-2 text-xs">
                <div className="font-semibold text-foreground border-b border-border pb-1">Geocoded Points</div>
                {filteredPoints.map((pt) => (
                  <div
                    key={pt.id}
                    onClick={() => setSelectedPoint(pt)}
                    className={`p-2 rounded cursor-pointer transition flex items-center justify-between gap-3 ${
                      selectedPoint.id === pt.id ? "bg-primary/10 text-primary font-bold" : "hover:bg-muted text-muted-foreground"
                    }`}
                  >
                    <span className="truncate">{pt.name}</span>
                    <span className="font-mono text-[10px]">{pt.lat.toFixed(2)}, {pt.lng.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Location Detail Panel (4 Cols) */}
          <div className="lg:col-span-4 rounded-lg border border-border bg-card p-5 space-y-4">
            <div className="flex items-center gap-2.5 border-b border-border pb-3">
              <div className="p-2 rounded bg-primary/10 text-primary">
                <Navigation className="size-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-foreground">{selectedPoint.name}</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-muted text-muted-foreground">
                  {selectedPoint.category}
                </span>
              </div>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <div className="text-muted-foreground mb-1">Geographic Coordinates</div>
                <div className="font-mono font-semibold bg-background p-2 rounded border border-border">
                  Latitude: {selectedPoint.lat} N • Longitude: {selectedPoint.lng} E
                </div>
              </div>

              <div>
                <div className="text-muted-foreground mb-1">Observed Operational Details</div>
                <p className="bg-background p-2.5 rounded border border-border text-foreground leading-relaxed">
                  {selectedPoint.details}
                </p>
              </div>

              <div>
                <div className="text-muted-foreground mb-1">Associated Operations ({selectedPoint.caseIds.length})</div>
                <div className="flex flex-wrap gap-1.5">
                  {selectedPoint.caseIds.map((cId) => (
                    <span key={cId} className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 font-semibold">
                      {cId}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
