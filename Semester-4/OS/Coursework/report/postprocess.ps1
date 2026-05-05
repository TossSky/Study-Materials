# Пост-обработка курсовой работы через Word COM (ГОСТ 7.32-2017):
#  - нумерация страниц в центре нижнего колонтитула (без номера на титульном)
#  - обновление поля TOC (автособираемое содержание)
#  - приведение абзацев TOC к выравниванию по левому краю, без курсива/жирного
#  - экспорт в PDF для визуального контроля

$Path = 'c:\Users\vyach\Study-Materials\Semester-4\OS\Coursework\report\Курсовая_ОС_Тоцкий.docx'
$Pdf  = 'c:\Users\vyach\Study-Materials\Semester-4\OS\Coursework\report\check.pdf'

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($Path)

foreach ($sec in $doc.Sections) { $sec.PageSetup.DifferentFirstPageHeaderFooter = $true }
$section = $doc.Sections.Item(1)
$section.Headers.Item(1).Range.Text = ''
$section.Headers.Item(2).Range.Text = ''

$footer = $section.Footers.Item(1)
$footer.Range.Text = ''
$rng = $footer.Range
$rng.Fields.Add($rng, 33, '', $false) | Out-Null
$footer.Range.Paragraphs.Item(1).Alignment = 1    # wdAlignParagraphCenter
$footer.Range.Paragraphs.Item(1).FirstLineIndent = 0
$footer.Range.Paragraphs.Item(1).LeftIndent = 0
$footer.Range.Font.Name = 'Times New Roman'
$footer.Range.Font.Size = 14
$section.Footers.Item(2).Range.Text = ''          # первая страница — без номера

$doc.Fields.Update() | Out-Null
$doc.Repaginate()
$doc.Fields.Update() | Out-Null

foreach ($toc in $doc.TablesOfContents) {
    $r = $toc.Range
    for ($p = 1; $p -le $r.Paragraphs.Count; $p++) {
        $para = $r.Paragraphs.Item($p)
        $para.Format.Alignment = 0
        $para.Range.Font.Name = 'Times New Roman'
        $para.Range.Font.Size = 14
        $para.Range.Font.Bold = 0
        $para.Range.Font.Italic = 0
    }
}

$doc.Save()
$doc.SaveAs([ref]$Pdf, [ref]17)
$pages = $doc.ComputeStatistics(2)
$words = $doc.ComputeStatistics(0)
$doc.Close($false)
$word.Quit()
"Pages: $pages | Words: $words"
