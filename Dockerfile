FROM continuumio/miniconda3

# Create environment + install torch + clean
RUN conda create -n ai-voice-studio python=3.11 -y && \
    \
    /opt/conda/envs/ai-voice-studio/bin/pip install \
        torch==2.9.1+cu128 \
        torchaudio==2.9.1+cu128 \
        --index-url https://download.pytorch.org/whl/cu128 \
    && \
    conda clean -a -y && \
    rm -rf /opt/conda/pkgs && \
    rm -rf /root/.cache/pip && \
    rm -rf /tmp/* && \
    find /opt/conda/envs/ai-voice-studio -name "*.pyc" -delete && \
    find /opt/conda/envs/ai-voice-studio -name "__pycache__" -type d -exec rm -rf {} +

# Make env active
ENV PATH="/opt/conda/envs/ai-voice-studio/bin:$PATH"

# Temporary build folder
WORKDIR /tmp/build

# Chatterbox instalation
COPY models/chatterbox/pyproject.toml ./models/chatterbox/
COPY models/chatterbox/src ./models/chatterbox/src/chatterbox/

# Install project and clean cache
RUN pip install ./models/chatterbox && \
    rm -rf /root/.cache/pip && \
    rm -rf /tmp/*

# Install main app requirements
COPY requirements.txt .
RUN pip install -r requirements.txt && \
    rm -rf /root/.cache/pip && \
    rm -rf /tmp/*

WORKDIR /app

# Copy rest of the project
# COPY . .

# Start app
CMD ["tail", "-f", "/dev/null"]