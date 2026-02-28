"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";

interface FadeInProps {
    children: React.ReactNode;
    delay?: number;
    duration?: number;
    className?: string;
    yOffset?: number;
    triggerOnce?: boolean;
}

export function FadeIn({
    children,
    delay = 0,
    duration = 0.8,
    className,
    yOffset = 30,
    triggerOnce = true
}: FadeInProps) {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: triggerOnce, margin: "-10% 0px" });

    return (
        <motion.div
            ref={ref}
            initial={{ opacity: 0, y: yOffset }}
            animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: yOffset }}
            transition={{
                duration,
                delay,
                ease: [0.21, 0.47, 0.32, 0.98] // A premium, elegant easing curve like wabi.ai
            }}
            className={className}
        >
            {children}
        </motion.div>
    );
}
