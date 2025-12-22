import React from 'react';
import PublicLayout from '../components/public/PublicLayout';

const AboutPage: React.FC = () => {
    return (
        <PublicLayout>
            <div className="bg-white">
                <div className="max-w-3xl mx-auto px-4 py-12">
                    <h1 className="text-3xl font-bold text-gray-900 mb-8">About MRM</h1>

                    <div className="prose prose-indigo max-w-none text-gray-500">
                        <p className="lead text-xl text-gray-600 mb-8">
                            The Model Risk Management (MRM) system is a comprehensive platform designed to govern the entire lifecycle of models used across the organization.
                        </p>

                        <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">Our Mission</h2>
                        <p className="mb-4">
                            To provide a robust framework for identifying, assessing, managing, and monitoring model risk, ensuring compliance with regulatory requirements and internal policies.
                        </p>

                        <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">Key Features</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                            <div className="border border-gray-200 rounded-lg p-4">
                                <h3 className="font-medium text-gray-900 mb-2">Model Inventory</h3>
                                <p className="text-sm">Centralized repository for all models, including metadata, documentation, and ownership details.</p>
                            </div>
                            <div className="border border-gray-200 rounded-lg p-4">
                                <h3 className="font-medium text-gray-900 mb-2">Validation Workflow</h3>
                                <p className="text-sm">Streamlined process for model validation, including submission, review, and approval stages.</p>
                            </div>
                            <div className="border border-gray-200 rounded-lg p-4">
                                <h3 className="font-medium text-gray-900 mb-2">Risk Assessment</h3>
                                <p className="text-sm">Tools for assessing inherent and residual risk, with automated scoring and reporting.</p>
                            </div>
                            <div className="border border-gray-200 rounded-lg p-4">
                                <h3 className="font-medium text-gray-900 mb-2">Monitoring & Reporting</h3>
                                <p className="text-sm">Ongoing monitoring of model performance and comprehensive reporting capabilities.</p>
                            </div>
                        </div>

                        <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">System Version</h2>
                        <p className="mb-4">
                            Current Version: 3.0.0
                        </p>
                    </div>
                </div>
            </div>
        </PublicLayout>
    );
};

export default AboutPage;
