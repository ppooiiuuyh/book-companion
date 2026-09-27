# PDF에 들어 있는 원본 JPEG를 재렌더링 없이 추출 (쪽 번호는 1부터)
import sys, pymupdf
pdf, pages, outdir = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], sys.argv[3]
d = pymupdf.open(pdf)
for p in pages:
    xref = d[p-1].get_images(full=True)[0][0]
    x = d.extract_image(xref)
    open(f"{outdir}/p{p:03d}.{x['ext']}", "wb").write(x["image"])
