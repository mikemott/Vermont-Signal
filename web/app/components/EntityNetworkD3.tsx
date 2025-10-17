'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface Node extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  type: string;
  weight?: number;
}

interface Link extends d3.SimulationLinkDatum<Node> {
  source: string | Node;
  target: string | Node;
  label: string;
}

interface EntityNetworkProps {
  entities: Array<{ id: string; label: string; type: string; weight?: number }>;
  connections: Array<{ source: string; target: string; label: string }>;
  entityColors: Record<string, string>;
  width?: number;
  height?: number;
  onEntityClick?: (entityId: string) => void;
}

export default function EntityNetworkD3({
  entities,
  connections,
  entityColors,
  width = 1200,
  height = 600,
  onEntityClick,
}: EntityNetworkProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile viewport
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;
    if (!entities || entities.length === 0) return;
    if (!connections || !Array.isArray(connections)) return;
    if (typeof window === 'undefined') return;

    // Clear previous content
    d3.select(svgRef.current).selectAll('*').remove();

    // Responsive dimensions
    const containerWidth = containerRef.current.clientWidth;
    const svgWidth = containerWidth;
    const svgHeight = isMobile ? 400 : 600;
    const baseNodeRadius = isMobile ? 50 : 40;
    const maxNodeRadius = isMobile ? 70 : 60;

    // Calculate node radius based on weight for visual hierarchy
    const weights = entities.map(e => e.weight || 1);
    const minWeight = Math.min(...weights);
    const maxWeight = Math.max(...weights);
    const weightRange = maxWeight - minWeight || 1; // Avoid division by zero

    const getNodeRadius = (weight: number = 1) => {
      // Scale radius from baseNodeRadius to maxNodeRadius based on weight
      const normalizedWeight = (weight - minWeight) / weightRange;
      return baseNodeRadius + (normalizedWeight * (maxNodeRadius - baseNodeRadius));
    };

    // Create SVG
    const svg = d3.select(svgRef.current)
      .attr('width', '100%')
      .attr('height', svgHeight)
      .attr('viewBox', [0, 0, svgWidth, svgHeight]);

    // Create data structures
    const nodes: Node[] = entities.map(e => ({
      id: e.id,
      label: e.label,
      type: e.type,
      weight: e.weight || 1,
    }));

    // Filter out invalid connections (missing source/target)
    const links: Link[] = connections
      .filter(c => c.source && c.target)
      .map(c => ({
        source: c.source,
        target: c.target,
        label: c.label || 'related',
      }));

    // Create force simulation with responsive parameters
    const linkDistance = isMobile ? 120 : 180;
    const chargeStrength = isMobile ? -600 : -1000;

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink<Node, Link>(links)
        .id(d => d.id)
        .distance(linkDistance))
      .force('charge', d3.forceManyBody().strength(chargeStrength))
      .force('center', d3.forceCenter(svgWidth / 2, svgHeight / 2))
      .force('collision', d3.forceCollide().radius(d => getNodeRadius((d as Node).weight) + 10));

    // Create container for zoom
    const g = svg.append('g');

    // Add zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Create arrow marker
    const arrowRefX = isMobile ? 40 : 35;
    svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', arrowRefX)
      .attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .append('path')
      .attr('d', 'M 0,-5 L 10,0 L 0,5')
      .attr('fill', '#e8e3db');

    // Create links
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#e8e3db')
      .attr('stroke-width', 2)
      .attr('marker-end', 'url(#arrowhead)');

    // Create link labels
    const linkLabel = g.append('g')
      .selectAll('text')
      .data(links)
      .join('text')
      .attr('font-size', 10)
      .attr('fill', '#6b7280')
      .attr('text-anchor', 'middle')
      .attr('dy', -5)
      .text(d => d.label);

    // Create node groups
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .call(
        d3.drag<SVGGElement, Node>()
          .on('start', dragstarted)
          .on('drag', dragged)
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .on('end', dragended) as any
      );

    // Add circles to nodes with tinted fill and variable size based on weight
    node.append('circle')
      .attr('r', d => getNodeRadius(d.weight))
      .attr('fill', d => {
        const color = entityColors[d.type] || '#6b7280';
        // Convert hex to rgba with transparency
        const r = parseInt(color.slice(1, 3), 16);
        const g = parseInt(color.slice(3, 5), 16);
        const b = parseInt(color.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, 0.1)`;
      })
      .attr('stroke', d => entityColors[d.type] || '#6b7280')
      .attr('stroke-width', isMobile ? 4 : 3)
      .style('filter', 'drop-shadow(0px 2px 4px rgba(0,0,0,0.1))');

    // Helper function to wrap text
    function wrapText(text: d3.Selection<SVGTextElement, Node, SVGGElement, unknown>) {
      text.each(function(this: SVGTextElement, d: Node) {
        const textElement = d3.select(this);
        const words = d.label.split(/\s+/);
        const dy = parseFloat(textElement.attr('dy') || '0');

        textElement.text(null);

        // If single word or short, just display it
        if (words.length === 1 || d.label.length < 15) {
          textElement.append('tspan')
            .attr('x', 0)
            .attr('y', -3)
            .attr('dy', dy + 'em')
            .text(d.label);
        } else {
          // Split into two lines for better fit
          const midpoint = Math.ceil(words.length / 2);
          const line1 = words.slice(0, midpoint).join(' ');
          const line2 = words.slice(midpoint).join(' ');

          textElement.append('tspan')
            .attr('x', 0)
            .attr('y', -8)
            .attr('dy', dy + 'em')
            .text(line1);

          textElement.append('tspan')
            .attr('x', 0)
            .attr('y', -8)
            .attr('dy', (1.1 + dy) + 'em')
            .text(line2);
        }
      });
    }

    // Add labels to nodes (inside circles)
    const fontSize = isMobile ? 12 : 11;
    const typeFontSize = isMobile ? 10 : 9;

    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 0)
      .attr('dy', 0)
      .attr('font-size', fontSize)
      .attr('font-weight', 600)
      .attr('fill', d => entityColors[d.type] || '#6b7280')
      .style('pointer-events', 'none')
      .call(wrapText);

    // Add type labels (below name, inside circle)
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', isMobile ? 24 : 20)
      .attr('font-size', typeFontSize)
      .attr('fill', '#6b7280')
      .text(d => d.type)
      .style('pointer-events', 'none');

    // Hover and click effects
    node
      .style('cursor', 'pointer')
      .on('mouseenter touchstart', function(event, d) {
        const currentRadius = getNodeRadius(d.weight);
        d3.select(this).select('circle')
          .transition()
          .duration(200)
          .attr('r', currentRadius + 10)
          .attr('stroke-width', isMobile ? 5 : 4);
      })
      .on('mouseleave touchend', function(event, d) {
        const currentRadius = getNodeRadius(d.weight);
        d3.select(this).select('circle')
          .transition()
          .duration(200)
          .attr('r', currentRadius)
          .attr('stroke-width', isMobile ? 4 : 3);
      })
      .on('click', function(event, d) {
        event.stopPropagation();
        event.preventDefault();
        if (onEntityClick) {
          onEntityClick(d.id);
        }
      });

    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as Node).x!)
        .attr('y1', d => (d.source as Node).y!)
        .attr('x2', d => (d.target as Node).x!)
        .attr('y2', d => (d.target as Node).y!);

      linkLabel
        .attr('x', d => ((d.source as Node).x! + (d.target as Node).x!) / 2)
        .attr('y', d => ((d.source as Node).y! + (d.target as Node).y!) / 2);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: d3.D3DragEvent<SVGGElement, Node, Node>, d: Node) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [entities, connections, entityColors, width, height, onEntityClick, isMobile]);

  return (
    <div ref={containerRef} className="w-full">
      <svg
        ref={svgRef}
        className="w-full border border-gray-200 rounded bg-white touch-none"
        style={{
          height: isMobile ? '400px' : '600px',
          touchAction: 'none'
        }}
      ></svg>
    </div>
  );
}
