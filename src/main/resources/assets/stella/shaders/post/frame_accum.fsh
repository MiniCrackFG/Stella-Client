#version 330

uniform sampler2D CurrentFrameSampler;
uniform sampler2D AccumPrevSampler;

layout(std140) uniform MotionBlurConfig {
    float BlendFactor;
};

in vec2 texCoord;

out vec4 fragColor;

void main() {
    vec4 current = texture(CurrentFrameSampler, texCoord);
    vec4 accum = texture(AccumPrevSampler, texCoord);
    fragColor = mix(accum, current, 1.0 - BlendFactor);
}
