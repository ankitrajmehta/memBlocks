import React from 'react';

function BlockManager({
  blocks,
  activeBlocks,
  currentBlock,
  onSelectBlock,
  onToggleBlock,
  onDeleteBlock,
  onCreateBlock
}) {
  const activeBlockIds = activeBlocks.map(b => b.block_id);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <h2 className="text-white font-semibold">Memory Blocks</h2>
          <button
            onClick={onCreateBlock}
            className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-700 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      {/* Active Context Section */}
      {activeBlocks.length > 0 && (
        <div className="p-4 border-b border-gray-800">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Active Context
          </h3>
          <div className="flex flex-wrap gap-2">
            {activeBlocks.map(block => (
              <div
                key={block.block_id}
                className="px-3 py-1.5 bg-indigo-600/20 text-indigo-400 text-sm rounded-lg flex items-center gap-2"
              >
                <span>{block.name}</span>
                <button
                  onClick={() => onToggleBlock(block)}
                  className="hover:text-white transition-colors"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Block List */}
      <div className="flex-1 overflow-y-auto p-2">
        {blocks.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <p className="text-sm">No memory blocks yet</p>
            <p className="text-xs mt-1">Create your first block to get started</p>
          </div>
        ) : (
          <div className="space-y-1">
            {blocks.map(block => {
              const isActive = activeBlockIds.includes(block.block_id);
              const isSelected = currentBlock?.block_id === block.block_id;
              
              return (
                <div
                  key={block.block_id}
                  onClick={() => onSelectBlock(block)}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    isSelected 
                      ? 'bg-indigo-600/20 border border-indigo-500/50' 
                      : 'hover:bg-gray-800 border border-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleBlock(block);
                        }}
                        className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                          isActive 
                            ? 'bg-indigo-600 border-indigo-600' 
                            : 'border-gray-600 hover:border-gray-500'
                        }`}
                      >
                        {isActive && (
                          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </button>
                      <span className="text-white text-sm font-medium">{block.name}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm('Delete this block? This cannot be undone.')) {
                          onDeleteBlock(block.block_id);
                        }
                      }}
                      className="text-gray-500 hover:text-red-400 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                  {block.description && (
                    <p className="text-gray-500 text-xs mt-1 ml-6 truncate">
                      {block.description}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-1 ml-6">
                    <span className="text-gray-600 text-xs">
                      {new Date(block.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default BlockManager;
