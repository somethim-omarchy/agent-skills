# Builds every CV into generated/: `make` (all), or `make general`, `make web`, `make devops`, `make rust`.
TECTONIC := ../.tools/tectonic
CACHE := $(abspath ../.tools/cache)
CVS := General Web DevOps Rust
PDFS := $(patsubst %,generated/Arbi_Kullakshi_%_CV.pdf,$(CVS))

.PHONY: all general web devops rust clean
all: $(PDFS)
general: generated/Arbi_Kullakshi_General_CV.pdf
web: generated/Arbi_Kullakshi_Web_CV.pdf
devops: generated/Arbi_Kullakshi_DevOps_CV.pdf
rust: generated/Arbi_Kullakshi_Rust_CV.pdf

generated/%.pdf: %.tex
	mkdir -p generated
	XDG_CACHE_HOME="$(CACHE)" $(TECTONIC) --outdir generated $<

clean:
	rm -f $(PDFS)
