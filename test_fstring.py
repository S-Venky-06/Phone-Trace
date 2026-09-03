map_name = 'map_12345'
script = f"""
        <script>
            window.activeMarker = null;
            window.updateActiveMarker = function(lat, lon) {{
                var mapInstance = {map_name};
                if (mapInstance) {{
                    if (!window.activeMarker) {{
                        var icon = L.divIcon({{
                            className: 'custom-beacon',
                            html: '<div style="background-color:#38BDF8; width:16px; height:16px; border-radius:50%; border: 3px solid white; box-shadow: 0 0 10px #38BDF8;"></div>',
                            iconSize: [16, 16],
                            iconAnchor: [8, 8]
                        }});
                        window.activeMarker = L.marker([lat, lon], {{icon: icon, zIndexOffset: 1000}}).addTo(mapInstance);
                    }} else {{
                        window.activeMarker.setLatLng([lat, lon]);
                    }}
                }}
            }};
            window.panToIncident = function(lat, lon) {{
                var mapInstance = {map_name};
                if (mapInstance) {{
                    mapInstance.flyTo([lat, lon], 14);
                }}
            }};
        </script>
"""
print(script)
