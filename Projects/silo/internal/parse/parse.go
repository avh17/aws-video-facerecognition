package parse

import (
	"context"
	"path/filepath"
	"strings"
	"os"
	"bytes"
	"github.com/ledongthuc/pdf"
	"github.com/yuin/goldmark"
)

type Document struct {
	Path string
	Text string
}

func ParseFile(_ context.Context, path string) (Document, error) {
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".pdf":
		return parsePDF(path)
	case ".md", ".markdown":
		return parseMarkdown(path)
	default:
		return Document{Path: path, Text: " "}, nil
	}
}

func parsePDF(path string) (Document, error) {
	f, r, err := pdf.Open(path)
	if err != nil { return Document{}, err }
	defer f.Close()
	
	var buf bytes.Buffer
	total := r.NumPage()
	for i := 1; i <= total; i++ {
		p := r.Page(i)
		if p.V.IsNull() {continue}
		t, _ := p.GetPlainText(nil)
		buf.WriteString("##PAGE ")
		buf.WriteString(strings.TrimSpace(t))
		buf.WriteString("\n")
	}
	return Document{Path: path, Text: buf.String()}, nil
}

func parseMarkdown(path string) (Document, error) {
	b, err := os.ReadFile(path)
	if err != nil { return Document{}, err }
	
	var out bytes.Buffer
	if err := goldmark.Convert(b, &out); err != nil { return Document{}, err }

	txt := out.String()
	txt = strings.ReplaceAll(txt, "<p>", "\n")
	txt = strings.ReplaceAll(txt, "</p>", "\n")
	
	return Document{Path: path, Text: txt}, nil
}