struct Params {
    time: f32,
    resolution: vec2<f32>,
    bg_color: vec3<f32>,
    accent_color: vec3<f32>,
};

@group(0) @binding(0) var<uniform> u_params: Params;

@fragment
fn fs_main(@builtin(position) frag_coord: vec4<f32>) -> @location(0) vec4<f32> {
    let uv = frag_coord.xy / u_params.resolution;
    
    // Compute 3 moving centers for the mesh gradient spots
    let t = u_params.time * 0.4;
    let p1 = vec2<f32>(0.25 + 0.15 * sin(t), 0.3 + 0.1 * cos(t * 1.5));
    let p2 = vec2<f32>(0.75 + 0.1 * cos(t * 1.2), 0.7 - 0.15 * sin(t * 0.8));
    let p3 = vec2<f32>(0.5 + 0.2 * sin(t * 0.9), 0.5 + 0.2 * cos(t * 1.1));

    // Distances from current pixel to centers
    let d1 = distance(uv, p1);
    let d2 = distance(uv, p2);
    let d3 = distance(uv, p3);

    // Convert distances to weights (closer means higher weight)
    let w1 = 1.0 - smoothstep(0.0, 0.8, d1);
    let w2 = 1.0 - smoothstep(0.0, 0.8, d2);
    let w3 = 1.0 - smoothstep(0.0, 0.9, d3);

    // Define three palette variations based on bg_color and accent_color
    let c1 = u_params.bg_color;
    let c2 = u_params.accent_color;
    // Synthesize a third midtone color from the palette
    let c3 = mix(c1, c2, 0.5);

    // Blend colors based on normalized weights
    let total_w = w1 + w2 + w3 + 0.001;
    let color = (w1 * c1 + w2 * c2 + w3 * c3) / total_w;

    return vec4<f32>(color, 1.0);
}
