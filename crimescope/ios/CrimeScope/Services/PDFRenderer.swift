import Foundation
import UIKit
import PDFKit

enum PDFRenderer {
    static func render(report: ReportSummary) -> URL {
        let pageRect = CGRect(x: 0, y: 0, width: 612, height: 792)
        let format = UIGraphicsPDFRendererFormat()
        let renderer = UIGraphicsPDFRenderer(bounds: pageRect, format: format)
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("crimescope-\(report.geoid).pdf")

        let title: NSAttributedString = attr("CrimeScope Risk Report", size: 22, weight: .bold)
        let region: NSAttributedString = attr(report.name + " · " + report.tier.rawValue, size: 16, weight: .semibold, color: tierUIColor(report.tier))
        let generated: NSAttributedString = attr("Generated " + Format.dateTime(report.generatedAt), size: 10, weight: .regular, color: .gray)

        let executive: NSAttributedString = sectionBlock("Executive summary", body: report.executiveSummary)
        let narrative: NSAttributedString = sectionBlock("Risk narrative", body: report.riskNarrative)
        let trust: NSAttributedString = sectionBlock("Trust notes", body: report.trustNotes)

        let driversText = report.drivers.map { d -> String in
            let glyph: String
            switch d.direction { case .up: glyph = "↑"; case .down: glyph = "↓"; case .neutral: glyph = "·" }
            return "  \(glyph)  \(d.label) — \(d.evidence) [impact \(Format.score(d.impact * 5))]"
        }.joined(separator: "\n")
        let drivers: NSAttributedString = sectionBlock("Drivers", body: driversText)

        let peerText = report.peerCompare.map { "  · \($0.name) (\($0.tier.rawValue), \(Format.score($0.score)))" }.joined(separator: "\n")
        let peers: NSAttributedString = sectionBlock("Peer comparison", body: peerText)

        let challengeText = report.challenges.map { "  · " + $0 }.joined(separator: "\n")
        let challenges: NSAttributedString = sectionBlock("Challenges & notes", body: challengeText)

        try? renderer.writePDF(to: url) { ctx in
            ctx.beginPage()
            var y: CGFloat = 48
            let margin: CGFloat = 48
            let width = pageRect.width - margin * 2

            y = draw(title, in: CGRect(x: margin, y: y, width: width, height: 40))
            y = draw(region, in: CGRect(x: margin, y: y + 4, width: width, height: 28))
            y = draw(generated, in: CGRect(x: margin, y: y + 2, width: width, height: 16))
            y += 12

            for block in [executive, narrative, trust, drivers, peers, challenges] {
                let neededHeight = block.boundingRect(
                    with: CGSize(width: width, height: .greatestFiniteMagnitude),
                    options: [.usesLineFragmentOrigin, .usesFontLeading],
                    context: nil
                ).height
                if y + neededHeight > pageRect.height - margin {
                    ctx.beginPage()
                    y = margin
                }
                y = draw(block, in: CGRect(x: margin, y: y, width: width, height: neededHeight))
                y += 16
            }
        }
        return url
    }

    @discardableResult
    private static func draw(_ string: NSAttributedString, in rect: CGRect) -> CGFloat {
        string.draw(with: rect, options: [.usesLineFragmentOrigin, .usesFontLeading], context: nil)
        let measured = string.boundingRect(
            with: CGSize(width: rect.width, height: .greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin, .usesFontLeading],
            context: nil
        )
        return rect.minY + measured.height
    }

    private static func sectionBlock(_ heading: String, body: String) -> NSAttributedString {
        let result = NSMutableAttributedString()
        result.append(attr(heading.uppercased(), size: 11, weight: .bold, color: .darkGray))
        result.append(attr("\n", size: 11, weight: .regular))
        result.append(attr(body, size: 12, weight: .regular))
        return result
    }

    private static func attr(
        _ text: String,
        size: CGFloat,
        weight: UIFont.Weight,
        color: UIColor = .black
    ) -> NSAttributedString {
        NSAttributedString(string: text, attributes: [
            .font: UIFont.systemFont(ofSize: size, weight: weight),
            .foregroundColor: color
        ])
    }

    private static func tierUIColor(_ tier: RiskTier) -> UIColor {
        tier.uiColor
    }
}
