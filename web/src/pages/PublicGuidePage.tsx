import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import PublicLayout from '../components/public/PublicLayout';
import { GUIDES, type Guide } from './PublicGuidesIndexPage';

export default function PublicGuidePage() {
    const { slug } = useParams();
    const [content, setContent] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const guide: Guide | undefined = GUIDES.find((g) => g.slug === slug);

    useEffect(() => {
        if (!guide) {
            setLoading(false);
            return;
        }

        const fetchGuide = async () => {
            try {
                setLoading(true);
                setError(null);
                const response = await fetch(`/guides/${guide.filename}`);
                if (!response.ok) {
                    throw new Error('Failed to load guide');
                }
                const text = await response.text();
                setContent(text);
            } catch (err) {
                setError('Unable to load this guide. Please try again later.');
                console.error('Failed to fetch guide:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchGuide();
    }, [guide]);

    return (
        <PublicLayout>
            <div className="max-w-5xl mx-auto px-4 py-10">
                {!guide ? (
                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                        <div className="text-lg font-semibold text-gray-900">Guide not found</div>
                        <div className="mt-2 text-sm text-gray-700">
                            Return to <Link className="text-blue-700 font-medium hover:underline" to="/guides">User Guides</Link>.
                        </div>
                    </div>
                ) : loading ? (
                    <div className="flex flex-col gap-6">
                        <header className="flex flex-col gap-2">
                            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{guide.title}</h1>
                            <p className="text-gray-700 max-w-3xl">{guide.description}</p>
                        </header>
                        <div className="bg-white border border-gray-200 rounded-lg p-6">
                            <div className="animate-pulse flex flex-col gap-4">
                                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                                <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                            </div>
                        </div>
                    </div>
                ) : error ? (
                    <div className="flex flex-col gap-6">
                        <header className="flex flex-col gap-2">
                            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{guide.title}</h1>
                        </header>
                        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                            <div className="text-red-700">{error}</div>
                        </div>
                        <div className="text-sm text-gray-600">
                            Back to <Link className="text-blue-700 font-medium hover:underline" to="/guides">User Guides</Link>.
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col gap-6">
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                            <Link className="text-blue-700 hover:underline" to="/guides">User Guides</Link>
                            <span>›</span>
                            <span className="text-gray-900">{guide.title}</span>
                        </div>

                        <div className="bg-white border border-gray-200 rounded-lg p-6 sm:p-8">
                            <article className="prose prose-gray max-w-none prose-headings:font-semibold prose-h1:text-2xl prose-h1:border-b prose-h1:pb-3 prose-h1:mb-6 prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4 prose-h3:text-lg prose-h3:mt-6 prose-a:text-blue-700 prose-a:no-underline hover:prose-a:underline prose-table:text-sm prose-th:bg-gray-100 prose-th:px-4 prose-th:py-2 prose-td:px-4 prose-td:py-2 prose-td:border prose-th:border prose-blockquote:border-blue-300 prose-blockquote:bg-blue-50 prose-blockquote:py-1 prose-blockquote:not-italic prose-code:before:content-none prose-code:after:content-none prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-normal prose-pre:bg-gray-100 prose-pre:text-gray-900 prose-pre:border prose-pre:border-gray-200 prose-pre:overflow-x-auto">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                                    {content || ''}
                                </ReactMarkdown>
                            </article>
                        </div>

                        <div className="text-sm text-gray-600">
                            Back to <Link className="text-blue-700 font-medium hover:underline" to="/guides">User Guides</Link>.
                        </div>
                    </div>
                )}
            </div>
        </PublicLayout>
    );
}
